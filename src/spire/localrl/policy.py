"""Local Qwen3-0.6B LoRA over every full-run decision, scored in one forward pass.

The older ``spire.language`` policy scores whole ``{"a":N}`` completions, one padded copy of
the prompt per candidate. A full-run prompt is ten times longer, so this policy reads the
next-token logits once at the answer position, one single-token symbol per legal choice. It
sees only the public ``Decision``: ``render_state`` is the API players' allowlisted view.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import time
from pathlib import Path

import torch

from spire.fullrun.llm import MONSTER_NOTES_PATH, render_state
from spire.localrl.facts import annotate
from spire.protocol import Decision

MODEL_DIRECTORY = Path.home() / (
    ".cache/spire-models/models--Qwen--Qwen3-0.6B/snapshots/"
    "c1899de289a04d12100db370d81485cdf75e47ca"
)
SYMBOLS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
HEADER = (
    "You play Slay the Spire as the Ironclad. Climb as high as you can: win fights, keep HP, "
    'build a strong deck. Answer with the symbol of the best choice as {"a":symbol}.'
)
ANSWER_PREFIX = '{"a":'
MAX_PROMPT_TOKENS = 1800
MONSTER_NOTES = json.loads(MONSTER_NOTES_PATH.read_text())


def render(observation: dict, labels: list[str]) -> str:
    choices = "\n".join(f"{SYMBOLS[i]}: {label}" for i, label in enumerate(labels))
    state = render_state(observation, MONSTER_NOTES)
    return f"{HEADER}\n\n{state}\n\nChoices:\n{choices}"


def render_v2(observation: dict, candidates: list[dict]) -> str:
    """As ``render``, each choice also saying what it does (``spire.localrl.facts``)."""
    labels = annotate(observation, candidates)
    choices = "\n".join(f"{SYMBOLS[i]}: {label}" for i, label in enumerate(labels))
    state = render_state(observation, MONSTER_NOTES)
    return f"{HEADER}\n\n{state}\n\nChoices:\n{choices}"


def load(adapter: Path | None, *, trainable: bool):
    """Base weights in bf16, adapter in float32 (PEFT's autocast); new if ``adapter`` is None."""
    from peft import LoraConfig, PeftModel, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIRECTORY, local_files_only=True)
    tokenizer.padding_side = "left"
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_DIRECTORY, local_files_only=True, dtype=torch.bfloat16,
        device_map={"": "cuda:0"}, attn_implementation="sdpa",
    )
    if adapter is None:
        config = LoraConfig(
            r=8, lora_alpha=16, lora_dropout=0.0, bias="none", task_type="CAUSAL_LM",
            target_modules=["q_proj", "k_proj", "o_proj", "v_proj"],
        )
        model = get_peft_model(model, config)
    else:
        model = PeftModel.from_pretrained(model, adapter, is_trainable=trainable,
                                          local_files_only=True)
    model.config.use_cache = False
    model.eval()
    return model, tokenizer


class Scorer:
    """Tokenized prompts and logits over the legal symbols."""

    def __init__(self, model, tokenizer):
        self.model, self.tokenizer = model, tokenizer
        self.symbol_ids = []
        for symbol in SYMBOLS:
            ids = tokenizer(symbol, add_special_tokens=False)["input_ids"]
            if len(ids) != 1:
                raise ValueError(f"Choice symbol {symbol!r} is not one token")
            self.symbol_ids.append(ids[0])
        self.device = next(model.parameters()).device

    def fingerprint(self) -> str:
        """The adapter's identity, recorded with every job so an arm is provable from disk."""
        from peft import get_peft_model_state_dict

        weights = get_peft_model_state_dict(self.model)
        digest = hashlib.sha256()
        for name in sorted(weights):
            digest.update(name.encode() + weights[name].float().cpu().numpy().tobytes())
        return digest.hexdigest()

    def encode(self, prompt: str) -> list[int]:
        text = self.tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}], tokenize=False,
            add_generation_prompt=True, enable_thinking=False,
        )
        ids = self.tokenizer(text + ANSWER_PREFIX, add_special_tokens=False)["input_ids"]
        return ids[-MAX_PROMPT_TOKENS:]

    def logits(self, encoded: list[list[int]], counts: list[int]) -> list[torch.Tensor]:
        """Next-token logits over each prompt's first ``count`` symbols (gradients allowed)."""
        width = max(map(len, encoded))
        pad = self.tokenizer.pad_token_id
        rows = [[pad] * (width - len(ids)) + ids for ids in encoded]
        mask = [[0] * (width - len(ids)) + [1] * len(ids) for ids in encoded]
        attention = torch.tensor(mask, device=self.device)
        output = self.model(
            input_ids=torch.tensor(rows, device=self.device), attention_mask=attention,
            # A left-padded row must keep the positions it had alone at collection.
            position_ids=(attention.cumsum(1) - 1).clamp(min=0), logits_to_keep=1,
        )
        last = output.logits[:, -1].float()
        return [last[i, self.symbol_ids[:count]] for i, count in enumerate(counts)]


class Encoded(list):
    """Token ids of a prompt, with the token that ends each choice line."""

    positions: list[int]


class PointerScorer(Scorer):
    """One score per choice, from the hidden state where its line ends, through a linear head.

    The symbol scorer must fit its comparison of every choice into one vector and then name a
    symbol. Here each choice has its own vector, so a choice's score does not depend on which
    symbol it drew. Same single forward pass. The head is saved beside the adapter. Scoring
    each legal choice from its own encoding is the pointer idea of Vinyals, Fortunato and Jaitly
    2015; no repository's code is copied.
    """

    HEAD = "head.pt"

    def __init__(self, model, tokenizer, head: Path | None = None):
        super().__init__(model, tokenizer)
        size = model.config.hidden_size
        self.head = torch.nn.Linear(size, 1).to(self.device, torch.float32)
        self.critic = torch.nn.Linear(size, 1).to(self.device, torch.float32)
        for layer in (self.head, self.critic):
            torch.nn.init.zeros_(layer.weight)
            torch.nn.init.zeros_(layer.bias)
        self.values: torch.Tensor | None = None
        if head is not None:
            self.load_head(head)

    def load_head(self, path: Path) -> None:
        saved = torch.load(path, map_location=self.device)
        self.head.load_state_dict(saved["head"])
        self.critic.load_state_dict(saved["critic"])

    def save(self, directory: Path) -> None:
        self.model.save_pretrained(directory)
        torch.save({"head": self.head.state_dict(), "critic": self.critic.state_dict()},
                   Path(directory) / self.HEAD)

    def fingerprint(self) -> str:
        digest = hashlib.sha256(super().fingerprint().encode())
        for weights in self.head.state_dict().values():
            digest.update(weights.float().cpu().numpy().tobytes())
        return digest.hexdigest()

    def encode(self, prompt: str) -> Encoded:
        text = self.tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}], tokenize=False,
            add_generation_prompt=True, enable_thinking=False,
        )
        tokens = self.tokenizer(text, add_special_tokens=False, return_offsets_mapping=True)
        ids, offsets = tokens["input_ids"], tokens["offset_mapping"]
        first = text.rindex("Choices:\n") + len("Choices:\n")
        ends, at = [], first
        for line in prompt[prompt.rindex("Choices:\n") + len("Choices:\n"):].split("\n"):
            at += len(line)
            ends.append(at - 1)  # the line's last character
            at += 1
        positions, token = [], 0
        for end in ends:
            while offsets[token][1] <= end:
                token += 1
            positions.append(token)
        cut = max(len(ids) - MAX_PROMPT_TOKENS, 0)
        encoded = Encoded(ids[cut:])
        encoded.positions = [position - cut for position in positions]
        return encoded

    def logits(self, encoded: list[Encoded], counts: list[int]) -> list[torch.Tensor]:
        width = max(map(len, encoded))
        pad = self.tokenizer.pad_token_id
        rows = [[pad] * (width - len(ids)) + ids for ids in encoded]
        mask = [[0] * (width - len(ids)) + [1] * len(ids) for ids in encoded]
        attention = torch.tensor(mask, device=self.device)
        output = self.model(
            input_ids=torch.tensor(rows, device=self.device), attention_mask=attention,
            position_ids=(attention.cumsum(1) - 1).clamp(min=0), logits_to_keep=1,
            output_hidden_states=True,
        )
        hidden = output.hidden_states[-1].float()
        self.values = self.critic(hidden[:, -1]).squeeze(-1)  # normalised return of each prompt
        scores = []
        for row, (ids, count) in enumerate(zip(encoded, counts)):
            places = [width - len(ids) + position for position in ids.positions[:count]]
            scores.append(self.head(hidden[row, places]).squeeze(-1))
        return scores


def scorer_for(model, tokenizer, adapter: Path) -> Scorer:
    """The scorer an adapter was trained with: a saved head means the pointer scorer."""
    head = Path(adapter) / PointerScorer.HEAD
    return PointerScorer(model, tokenizer, head) if head.exists() else Scorer(model, tokenizer)


def log_probs(logits: torch.Tensor, allowed: list[int], temperature: float) -> torch.Tensor:
    """Log-probabilities over the allowed choices, in ``allowed`` order."""
    return torch.log_softmax(logits[allowed] / temperature, dim=0)


def playable(observation: dict, labels: list[str]) -> list[int]:
    """Choices the game can carry out. Taking or buying a potion with every slot full changes
    nothing, so CommunicationMod never answers and the run hangs (seen 2026-11-06, floors 3, 5)."""
    full = all(potion.get("id") != "Potion Slot" for potion in observation.get("potions", []))
    shop = (observation.get("screen_state") or {}).get("potions", [])
    names = tuple(f"buy {potion.get('name')} for " for potion in shop)
    dead = ("take potion", *names)
    usable = [i for i, label in enumerate(labels) if not (full and label.startswith(dead))]
    return usable or list(range(len(labels)))


class LocalPolicy:
    """One instance per run. ``temperature`` 0 is greedy; steps collect for the learner.

    JUDGEMENT: Loop mask — Claude, 2026-11-06, owner away: a state seen before never repeats
    its earlier choice while another is left, because a weak policy otherwise loops between
    screens that do not change the state (reopening a skipped reward, selecting and deselecting
    a card). Floors therefore measure the model plus this mask.
    """

    def __init__(self, scorer: Scorer | None, *, temperature: float, seed: int, prompt: int = 1):
        self.scorer, self.temperature, self.prompt = scorer, temperature, prompt
        self.random = random.Random(seed)
        self.steps: list[dict] = []
        self.tried: dict[str, set[int]] = {}
        self._metadata = None
        self.api = None

    def _choose(self, prompt: str, allowed: list[int], count: int) -> tuple[int, float]:
        if self.scorer is None:  # the uniform random control
            return self.random.choice(allowed), -math.log(len(allowed))
        with torch.inference_mode():
            logits = self.scorer.logits([self.scorer.encode(prompt)], [count])[0]
        if self.temperature == 0:
            best = logits[allowed].argmax().item()
            return allowed[best], 0.0
        probabilities = torch.softmax(logits[allowed] / self.temperature, dim=0).tolist()
        index = self.random.choices(range(len(allowed)), weights=probabilities)[0]
        return allowed[index], math.log(max(probabilities[index], 1e-12))

    def choose(self, decision: Decision):
        started = time.monotonic()
        data = decision.to_dict()
        observation = data["observation"]
        count = min(len(decision.candidates), len(SYMBOLS))
        labels = [candidate["label"] for candidate in data["candidates"][:count]]
        prompt = (render_v2(observation, data["candidates"][:count]) if self.prompt == 2
                  else render(observation, labels))
        key = hashlib.sha256(prompt.encode()).hexdigest()
        tried = self.tried.setdefault(key, set())
        usable = playable(observation, labels)
        allowed = [i for i in usable if i not in tried] or usable
        index, log_prob = self._choose(prompt, allowed, count)
        tried.add(index)
        self.steps.append({
            "prompt": prompt, "count": count, "allowed": allowed, "index": index,
            "log_prob": log_prob, "observation": lite(observation), "label": labels[index],
        })
        self._metadata = {"type": "local", "selected_index": index, "log_prob": log_prob,
                          "allowed": allowed, "seconds": time.monotonic() - started}
        return decision.candidates[index]

    def choice_metadata(self, decision_id: str) -> dict:
        return self._metadata


def lite(observation: dict) -> dict:
    """The public numbers the reward and the baseline read."""
    combat = observation.get("combat_state") or {}
    player = combat.get("player") or {}
    monsters = [m for m in combat.get("monsters", []) if m.get("current_hp", 0) > 0
                and not m.get("is_gone")]
    return {
        "act": observation.get("act"), "floor": observation.get("floor"),
        "hp": observation.get("current_hp"), "max_hp": observation.get("max_hp"),
        "gold": observation.get("gold"), "deck": len(observation.get("deck", [])),
        "relics": len(observation.get("relics", [])),
        "potions": sum(p.get("id") != "Potion Slot" for p in observation.get("potions", [])),
        "screen": observation.get("screen_type"), "room": observation.get("room_type"),
        "turn": combat.get("turn", 0), "energy": player.get("energy", 0),
        "block": player.get("block", 0), "hand": len(combat.get("hand", [])),
        "enemy_hp": sum(m.get("current_hp", 0) for m in monsters),
        "enemies": len(monsters),
        "incoming": sum(max(m.get("move_adjusted_damage", 0), 0) * m.get("move_hits", 1)
                        for m in monsters),
    }


def enable_training(model) -> list:
    """Gradient checkpointing keeps a minibatch of long prompts inside the 12 GB card."""
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.enable_input_require_grads()
    return [p for p in model.parameters() if p.requires_grad]
