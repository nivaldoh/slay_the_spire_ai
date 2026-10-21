"""Follow a battle job live, beside the game, or wait for its next event.

    python -m twwarhammer3 watch [runs/twwarhammer3/battle/<job>[/episode-NNNN]] [--prompts]
    python -m twwarhammer3 watch runs/twwarhammer3/battle/<job> --next [--stall-minutes M]

Without a path the live feed follows the job named in the bridge's ``session.json``. It tails
each episode's ``trace.jsonl`` as the job writes it and prints:
- each model request (``->``): the battle time and both sides' strength in the state it was
  built from, and a commander prompt's dropped or rejected report (``--prompts`` prints it
  whole);
- each reply (``<-``): a commander's plan with its age, think time and reason, or the
  direct controller's orders and reason, and the notes whenever they change;
- each episode's armies, engine rejections, invalid batches, a strength line with the spend
  so far every 30 s of battle time, and each result.
A finished job or a finished episode is printed once.

``--next`` (only with a job directory) is for an agent running it in the background: it
prints once and exits, when an episode finishes (its digest's first line, final state and
notes), when the job is not running, when nothing in the job has changed for the stall time
(STALL_S, ``--stall-minutes``) while it runs, or when no manifest appears within START_S
(the job refused to start; its log says why). It only reads evidence.
"""

import json
import time
from pathlib import Path

from twwarhammer3.battle.commander import REPORT_HEADER, describe_plan
from twwarhammer3.battle.digest import build_warning, episode_digest, strength
from twwarhammer3.battle.llm import describe_orders, short_type

STATUS_S = 30
STALL_S = 120
START_S = 60


class Feed:
    """Turns trace records into summary lines; one per episode."""

    def __init__(self, name: str, prompts: bool = False):
        self.name = name
        self.prompts = prompts
        self.observation: dict = {}
        self.status_s = 0.0
        self.usd = 0.0
        self.notes = None
        self.pending: dict[str, list[dict]] = {}

    def lines(self, record: dict) -> list[str]:
        kind = record["kind"]
        if kind in ("observation", "roster"):
            self.observation = record["observation"]
        if kind == "roster":
            self.status_s = self.observation.get("time_ms", 0) / 1000
            return self._roster(record["observation"])
        if kind == "observation":
            seconds = self.observation.get("time_ms", 0) / 1000
            if seconds - self.status_s >= STATUS_S:
                self.status_s = seconds
                return [f"{seconds:5.0f}s   {strength(self.observation)}  ${self.usd:.4f}"]
        if kind == "decision":
            return self._decision(record)
        if kind == "ack":
            orders = self.pending.pop(record["request"], [])
            return [f"{record['ack']['applied_ms'] / 1000:5.0f}s x engine rejected"
                    f" {describe_orders([orders[r['index'] - 1]])}: {r.get('error')}"
                    for r in record["ack"].get("results", [])
                    if not r.get("ok") and 0 < (r.get("index") or 0) <= len(orders)]
        if kind == "invalid":
            return [f"        invalid orders: {record['error']}"]
        if kind == "result":
            final = record["observation"].get("final") or {}
            left = ", ".join(f"{side} {final[side]['men'] / final[side]['men0']:.0%} left"
                             for side in ("friendly", "enemy")
                             if (final.get(side) or {}).get("men0"))
            return [f"== {self.name}: {record['observation'].get('result')} at"
                    f" {record['observation'].get('time_ms', 0) / 1000:.0f} s; {left};"
                    f" ${self.usd:.4f}"]
        return []

    def _roster(self, observation: dict) -> list[str]:
        armies = observation.get("armies", {})
        sides = []
        for label, side, units in (("us", "player", observation.get("friendly", [])),
                                   ("them", "enemy", observation.get("enemy_roster", []))):
            types = ", ".join(short_type(unit.get("type")) for unit in units)
            sides.append(f"   {label} ({armies.get(side, {}).get('faction', '?')}): {types}")
        return [f"== {self.name}"] + sides

    def _decision(self, record: dict) -> list[str]:
        behavior = record.get("behavior") or {}
        seconds = record["time_ms"] / 1000
        lines = []
        if record["orders"]:
            self.pending[record["request"]] = record["orders"]
        attempts = behavior.get("attempts") or []
        self.usd += sum(attempt.get("usd", 0) for attempt in attempts)
        think = sum(attempt.get("seconds", 0) for attempt in attempts)
        if behavior.get("type") == "llm" and "prompt" in behavior:
            lines += self._request(seconds, behavior)  # the direct controller blocks
        if "plan" in behavior:
            lines.append(f"{seconds:5.0f}s <- plan {behavior['plan_age_s']:.1f} s old"
                         f" ({think:.1f} s think): {behavior['reason']}")
            plan = describe_plan(behavior["plan"])
            if behavior.get("abilities"):
                plan += "; " + describe_orders(behavior["abilities"])
            lines.append("         " + plan)
            lines += [f"         dropped {item}" for item in behavior.get("dropped", [])]
        elif behavior.get("reason"):
            lines.append(f"{seconds:5.0f}s <- {describe_orders(record['orders'])}"
                         f" ({think:.1f} s think): {behavior['reason']}")
        if behavior.get("notes") and behavior["notes"] != self.notes:
            self.notes = behavior["notes"]
            lines.append("         notes: " + self.notes.replace("\n", " / "))
        if behavior.get("type") == "commander" and "prompt" in behavior:
            lines += self._request(seconds, behavior)  # sent after adopting the last plan
        return lines

    def _request(self, seconds: float, behavior: dict) -> list[str]:
        prompt = behavior["prompt"]
        lines = [f"{seconds:5.0f}s -> {behavior.get('model', 'model')}:"
                 f" {strength(self.observation)}; {len(prompt)} chars"]
        if self.prompts:
            return lines + ["         " + line for line in prompt.splitlines()]
        if REPORT_HEADER in prompt:
            report = prompt.split(REPORT_HEADER, 1)[1].split("\n\n", 1)[0]
            lines += [f"         reported: {item}" for item in report.splitlines()
                      if item != "(none)"]
        return lines


def _print(line: str) -> None:
    print(line, flush=True)


def episode(path: Path, prompts: bool = False, out=_print, poll: float = 0.3) -> None:
    """Print an episode's records as the job writes them, until its result is saved."""
    feed, buffer, finished = Feed(path.name, prompts), "", False
    with (path / "trace.jsonl").open() as handle:
        while True:
            chunk = handle.readline()
            if chunk:
                buffer += chunk
                if buffer.endswith("\n"):
                    for line in feed.lines(json.loads(buffer)):
                        out(line)
                    buffer = ""
            elif finished:
                return
            else:
                # result.json is written after the last record: read once more after it.
                # A killed job never writes it, so a job no longer running also ends this.
                finished = (path / "result.json").exists() or not _running(path.parent)
                if not finished:
                    time.sleep(poll)


def _running(job: Path) -> bool:
    manifest = job / "manifest.json"
    return not manifest.exists() or json.loads(manifest.read_text())["status"] == "running"


def follow(path: Path, prompts: bool = False, out=_print, poll: float = 1.0) -> None:
    """Print an episode, or a job's episodes in order, while the job writes them."""
    if (path / "trace.jsonl").exists():
        episode(path, prompts, out)
        return
    index, warned = 0, False
    while True:
        if not warned and (warning := build_warning(path)):
            out(warning)
            warned = True
        directory = path / f"episode-{index:04d}"
        if (directory / "trace.jsonl").exists():
            episode(directory, prompts, out)
            index += 1
            continue
        if not _running(path):
            return
        time.sleep(poll)


def check(job: Path, seen: int, stall_s: float = STALL_S) -> str | None:
    """The event since ``seen`` episodes had finished, or None if there is none yet."""
    path = job / "manifest.json"
    if not path.exists():
        return None
    manifest = json.loads(path.read_text())
    ended = "" if manifest["status"] == "running" else f"job {manifest['status']}" + (
        f": {manifest['error']}" if manifest.get("error") else "")
    warning = build_warning(job)
    warning = f"{warning}\n" if warning else ""
    if len(manifest["episodes"]) > seen:
        episode = job / manifest["episodes"][seen]["episode"]
        return warning + episode_digest(episode, decisions=False) + (f"\n{ended}" if ended else "")
    if ended:
        return warning + ended
    # The game's log while it starts, the menu log during setup, then the traces.
    files = [path, job / "game.log", job / "menu.log", *job.glob("episode-*/trace.jsonl")]
    newest = max((file for file in files if file.exists()), key=lambda file: file.stat().st_mtime)
    age = time.time() - newest.stat().st_mtime
    if age > stall_s:
        return f"STALL: {newest.relative_to(job)} unchanged for {age:.0f} s"
    return None


def next_event(job: Path, stall_s: float = STALL_S, poll: float = 5) -> str:
    """Wait for the job's next event (see ``check``) and return it."""
    path = job / "manifest.json"
    seen = len(json.loads(path.read_text())["episodes"]) if path.exists() else 0
    started = time.monotonic()
    while (event := check(job, seen, stall_s)) is None:
        if not path.exists() and time.monotonic() - started > START_S:
            log = job.with_name(f"{job.name}.log")
            tail = log.read_text().splitlines()[-3:] if log.exists() else ["no log"]
            return "NOT STARTED: " + " | ".join(tail)
        time.sleep(poll)
    return event
