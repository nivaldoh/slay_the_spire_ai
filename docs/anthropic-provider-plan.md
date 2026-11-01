# Plan: add the Anthropic API as a third provider

Status (2026-10-31, evening): implemented when the owner said "Implement docs/anthropic-provider-plan.md"; five of the six recommendations below were taken as written. What differs from the plan: the owner's key is not scoped to one workspace, so every request also sends `anthropic-workspace-id` from `GAMEAI_ANTHROPIC_WORKSPACE_ID` (required for provider `anthropic`), and the key carries its own $200 budget instead of a dedicated workspace's spend limit (recommendation 4). A 529 is resent for Anthropic only. Results of the paid smoke: [WH3 log](twwarhammer3/log.md#2026-10-31-anthropic-provider-added). Planning reports, the change card and reviews are in `runs/anthropic-provider/`.

## Decisions for the owner

1. **Training on Claude outputs.** Anthropic's Commercial Terms §D.4 forbid using the API "to train competing AI models"; the Usage Policy page (effective Nov 12, 2026) bars using outputs to train an AI model ("model scraping" or "model distillation") without prior authorization. `gameai/sft.py` keeps only OpenRouter rows by default, so Claude rows are already excluded. Recommendation: keep that, and add Anthropic to the two exporters' terms warnings, which name only OpenAI.
2. **Refusal fallbacks: off.** Anthropic's opt-in beta reruns a refused request on another model, so a benchmark row would measure a different model than the one named (the reason OpenRouter backends are pinned with `allow_fallbacks: False`). Recommendation: never send `fallbacks`; a refusal behaves like an OpenAI refusal today (no JSON, the harness re-asks, it ends as an invalid reply).
3. **Models and modes.** `claude-haiku-5-5` ($0.10 / $0.01 / $0.50 per M input / cache-read / output tokens), `claude-sonnet-5-5` ($2 / $0.10 / $10), `claude-opus-5-5` ($4 / $0.20 / $20), each at effort `low`, `medium`, `high`, `xhigh`, `max`. Haiku first, so it becomes the WH3 default like `gpt-6-luna` is for OpenAI. Thinking can't be turned off on Opus 5.5; on Haiku (`disabled`) and Sonnet (`between_tools`) only at `high` or below, so a `none` mode needs a choice of which effort goes with it. Recommendation: leave `none` for a later decision. Fable 5.1 ($10 / $50) only if wanted.
4. **Money.** Recommendation: a dedicated Console workspace with a monthly spend limit (the owner picks the allowance), plus one ledger per game as today. The workspace limit must sit above the total of the ledger budgets: when Anthropic's limit trips it returns HTTP 400, which WH3 counts as the model failing (the battle plays on with no orders and gets scored); our ledger stops a job cleanly as an operator stop, so it must trip first. Making that 400 an operator stop would edit the marked "Operator errors" spot in `src/twwarhammer3/battle/play.py:369`; recommendation: leave it and rely on the ordering.
5. **Our HTTP code or the official SDK.** Anthropic's guidance prefers its `anthropic` Python SDK. Recommendation: reuse our standard-library `post()`. The SDK adds a new dependency tree (`uv.lock` has neither httpx nor pydantic), its retries would have to be disabled so the ledger sees every attempt, and SDK upgrades can change the API version it sends; with our code the version is one pinned constant.
6. **Size of the paid test.** `providers.py` says each declared effort was "accepted by one live schema call". Recommendation: honour that: about 18 tiny calls, at most about $0.10, under a $0.25 cap. Cheaper option: Haiku only (under $0.01), and declare only Haiku's efforts until the others are checked.

## API key setup (the owner does this)

In the Anthropic Console:

1. Add credits or a payment method (otherwise `402`).
2. Create a workspace, for example `game-ai`, and set its monthly spend limit (the Default workspace can't have one).
3. Create a key: **Linked account: yourself**, **scoped to `game-ai`** (an unscoped key needs an `anthropic-workspace-id` header on every request), expiry 30 days or a custom 90.

In the owner's own WSL terminal (not through `!`, never pasted into a chat):

```bash
(umask 077; mkdir -p ~/.config/anthropic-api; read -rsp 'Anthropic API key: ' key; echo; printf '%s\n' "$key" > ~/.config/anthropic-api/api_key)
stat -c %a ~/.config/anthropic-api/api_key                         # expect 600
grep -q '^sk-ant-api' ~/.config/anthropic-api/api_key && echo ok   # checks the format, prints no secret
```

The key never appears on screen, in shell history or in `ps`. If it was copied through Windows, clear the clipboard history (Win+V, Clear all). Jobs get only the path, on each command as OpenRouter's is today: `GAMEAI_ANTHROPIC_API_KEY_FILE=~/.config/anthropic-api/api_key uv run ...` (`~/.bashrc` returns early in non-interactive shells, so an export there would not reach jobs). Never export `ANTHROPIC_API_KEY`: Claude Code reads it and can bill its own usage to it, and the repo will not read it, so a key exported for another tool can't charge game calls outside the capped workspace. Avoid `~/.config/anthropic/` (the `ant` CLI's profiles). If the key leaks, **Disable** it in the Console (reversible). Agents never read or print the file.

## Design

The OpenAI Responses-API shape stays the repo's only internal format. Reports, exporters, stats, the SFT builder and the retry logic read it: `request["instructions"]`, `request["input"][0]["content"]`, `output` items, `usage.input_tokens`, `incomplete_details.reason`. Two private functions in `src/gameai/llm.py` translate to and from Anthropic's Messages API, and only `post()` calls them. Choosing a provider stays `--provider anthropic` or `llm_rules@claude-sonnet-5-5/high`; no game code knows the wire format.

### Request translation (`_to_messages`, once, before the retry loop)

| What `Model.call` builds | What is sent |
|---|---|
| `model`, `instructions`, `input` | `model`, `system`, `messages` |
| `max_output_tokens` | `max_tokens` (includes thinking, as with OpenAI) |
| `reasoning.effort` | `output_config.effort` |
| `text.format.schema` (drop `type`, `name`, `strict`) | `output_config.format = {"type": "json_schema", "schema": ...}` (one `output_config` object with `effort`) |
| `reasoning.summary == "auto"` | `thinking = {"type": "adaptive", "display": "summarized"}` |
| `store` | dropped |
| any other top-level key | `ValueError` before anything is sent |

A Haiku request over 100,000 bytes also raises: a margin under Haiku's 100K-token step, above which every Haiku price is five times higher (`usage_cost` would otherwise undercharge by 5x and pass the reservation check). The server adds its own system prompt for thinking and structured outputs, so this is a margin, not a proof. Today's prompts are a few thousand tokens.

### Reply translation (`_from_messages`)

Runs after the reply is read, outside the retry try-block, and never raises on unknown content (a raise there would resend a billed call, or escape uncharged).

| Anthropic reply | Internal reply |
|---|---|
| `id`, `model` | copied (ledger `response_id`, report dedupe, `actual_model`, card identity) |
| `stop_reason: end_turn` | `status: completed`, `incomplete_details: None` |
| `stop_reason: max_tokens` | `status: incomplete`, `incomplete_details.reason: max_output_tokens` (the cut-off notice works) |
| `stop_reason: refusal` | completed message whose only part is a refusal part carrying `stop_details` (OpenAI's refusal shape) |
| any other stop reason | `status: incomplete` with that reason |
| `text` blocks | one `message` item with `output_text` parts |
| `thinking` blocks with text | `reasoning` items with `summary_text` parts; skip empty text (display `omitted`) and `redacted_thinking` |
| usage | `input_tokens = input + cache_read + cache_creation` (Anthropic's `input_tokens` excludes both); `input_tokens_details.cached_tokens = cache_read`; `output_tokens` as is (includes thinking); `output_tokens_details.reasoning_tokens = thinking_tokens`; null or missing fields count as 0 |

With that usage shape the existing OpenAI cost formula prices Anthropic. Nothing is cached: we never send `cache_control`, and Anthropic never caches without it.

### Code changes

1. `src/gameai/providers.py`: `ANTHROPIC` (URL `https://api.anthropic.com/v1/messages`, key variables `GAMEAI_ANTHROPIC_API_KEY` and `GAMEAI_ANTHROPIC_API_KEY_FILE`, the prices and efforts above); the API version constant `2026-10-21` (latest; for Messages it only removes `temperature`/`top_p`/`top_k` and two citation/document shapes we never send); `"anthropic"` appended last to `PROVIDERS` (the regex in `tests/gameai/test_providers.py:224` depends on the order); `routing()` returns `{}` for every provider except OpenRouter (today it returns OpenRouter's fields for anything not OpenAI; they would be sent to Anthropic and recorded in cards via `controllers.py:116,136`, `cards.py:261`, `report.py:231`).
2. `src/gameai/llm.py`: the two functions; in `post()` the `anthropic-version` header (the existing `Authorization: Bearer` is Anthropic's documented form for API keys; `x-api-key` is "legacy"); 529 (overloaded) added to `TRANSIENT_HTTP`; `Model.call` asks for summaries for Anthropic too (`:237`, same bill either way); both module docstrings, which say "Responses API".
3. Ledgers: Spire `LEDGERS` (`src/spire/fullrun/llm.py:31`) gains `runs/spire-anthropic-spend.jsonl`. WH3 gets a `LEDGERS` dict in `src/twwarhammer3/__main__.py` (`LEDGER_PATH.with_name("anthropic-spend.jsonl")`), used at `:398` and `:496` (without it an Anthropic WH3 job silently charges the OpenAI ledger). Not in `battle/llm.py`: that file's hash is the llm policy's card identity (`controllers.py:103`, `cards.py:259`, `team.py:446`). Create both ledger files deliberately, after the owner's OK.
4. Provider text: the terms warnings in `src/spire/fullrun/export.py` (`_data_card` counts only `openai/` rows at `:432-433`, text at `:522-525`) and `src/twwarhammer3/battle/export.py:490-494`; `src/gameai/sft.py:268-271`; `src/spire/fullrun/export.py:471` ("OpenAI returns reasoning summaries"); the WH3 `--model` help at `src/twwarhammer3/__main__.py:148-149`.
5. Tests (offline): translation both ways including the usage sum and an unknown key raising, with fixtures built from the API field reference (its example reply is placeholder data); one `Model.ask` through `post()` with `urlopen` faked, checking the version header and the cut-off notice on an `incomplete` reply; one assert added to the existing `routing` test; `tests/twwarhammer3/test_wh3_cli.py:140` changed from patching `OPENROUTER_LEDGER_PATH` to `monkeypatch.setitem(cli.LEDGERS, ...)`, parametrized over OpenRouter and Anthropic like `tests/fullrun/test_spire_cli.py:20-30` (the regression for the wrong-ledger bug).
6. Docs: `docs/references.md` (the sources below); key and ledger lines in `docs/twwarhammer3/README.md` (`:184`, `:203`, `:222-226`), `docs/twwarhammer3/controllers.md` (`:225-240`), `docs/spire/fullrun/README.md` (`:30-41`), `docs/spire/AGENTS.md` (`:66`, `:133-136`), `runs/README.md`; the provider-terms section of `docs/posttraining.md` (`:228-239`, `:256-257`); the `AGENTS.md` Evidence paragraph reworded in place (the file is at its 200-line limit, `tests/test_repo_rules.py:31`); a log entry; `docs/state.md` (about 120 lines).

Unchanged: prompts and snapshots, schemas, CLI flags (`choices=PROVIDERS`), reports, stats, the SFT builder, every WH3 policy file (no card identity change).

Schemas, checked offline: Spire (`src/spire/fullrun/llm.py:46-55`), WH3 orders (`src/twwarhammer3/battle/llm.py:41-82`) and commander (`src/twwarhammer3/battle/commander.py:48-67`) use only `type`, `properties`, `required`, `additionalProperties: false` (on every object), `enum`, `anyOf`, `items`; all fields required. Union-typed fields (type lists plus `anyOf`): 1, 9 and 10, against Anthropic's limit of 16. Anthropic does not guarantee the capitalization of string enum values; our parsers match exactly, so a slip shows as an invalid reply. Watch for it in the live test; do not normalize.

## Paid live test

A throwaway script in `runs/anthropic-smoke/` with its own ledger and a $0.25 cap:

1. Free: `GET /v1/models/{id}` capability flags for the three models, compared with the table in `providers.py`.
2. One `Model.call` per model × effort (15 calls, no retries), Spire schema, `max_output_tokens=256`; an HTTP 200 counts as accepted. Cut-off replies exercise the `incomplete` mapping.
3. One Haiku `Model.ask` per game schema (3 calls), summaries on, one at `high`, with a larger output cap so replies complete.
4. Optional, a day later: compare the ledger's token counts with the Console Usage page (the one check not resting on our own price table).

A pass shows the key file loads, the headers authenticate, every declared effort and schema is accepted, replies parse, summaries land where the exporters look, and the ledger charges reported usage. It does not show gameplay, latency under load, or behaviour on 529s, timeouts or real refusals. If the owner wants it repeatable (for example after an API version change), propose it for `docs/agreed-checks.md`.

## JUDGEMENT markers the change adds

- The API version pin; the model and effort table (no `none`); Haiku as WH3's default Anthropic model.
- No fallbacks; refusals handled like OpenAI's (re-asked as an invalid reply).
- Summaries on whenever exchanges are recorded. Anthropic writes summaries with a separate model; whether that adds latency is unverified, and WH3 counts latency.
- 529 counted as uncertain billing: retried and charged at the reservation each time, so a burst eats budget early.
- Effort names don't mean equal compute across providers: OpenAI `high` and Anthropic `high` differ, so cross-provider comparisons at one label rest on this marker.

## Notes for the implementing session

- `post()` (`src/gameai/llm.py:94-140`): the body is encoded at `:98`, before the loop; translate there. The try at `:105-137` catches `(OSError, http.client.HTTPException, ValueError)` and resends, so decode after the read and outside that try. `_call_reserved` catches only `APIError` (`:254`) and `call` releases the reservation in `finally` (`:248`): a `ValueError` from `_to_messages` propagates uncharged, which is right because nothing was sent. In WH3 it ends the episode as a non-forfeit `PolicyFailure` (`battle/play.py:688`), scored as a forfeit (`cards.py:89-91`).
- `llm.py:294-297` adds null `backend`, `backend_model`, `router_attempts` to every non-OpenAI attempt, and `provider_processing_ms` comes from the `openai-processing-ms` header, so it is None for Anthropic: latency comparisons rest on wall time (`report.py:113-114`, `replay.py:292-293`). Optional: change `:294` to `== "openrouter"`.
- The API version reaches evidence only through the job's source fingerprint; the recorded `request` stays the Responses-shaped body.
- Failure handling: `battle/play.py:369` stops for `HTTP 401`, `HTTP 402` or messages ending "and stopped"; Anthropic's 400 (own spend limit) and 429 `enforced_spend_limit_reached` become forfeits (`:381-386`, `:687-690`); Spire waits on `HTTP 429` up to 945 s per decision (`src/spire/fullrun/llm.py:287`).
- `tests/plants.toml` has no plant on `providers.py`, `gameai/llm.py`, `fullrun/llm.py` or `twwarhammer3/__main__.py`. Do not change the `Ledger(..., must_exist=True)` lines in `src/spire/__main__.py` and `battle/controllers.py`: plants quote them (agreed check in `docs/agreed-checks.md:45-48`).
- `tests/test_repo_rules.py` `KEY` regex already matches `sk-ant-api03-...` keys (digit plus upper case).
- Uncommitted files at planning time that belong to someone else: `docs/twwarhammer3/gap-plan.md`, `docs/thesis/`, `tests/twwarhammer3/prompts/TODO.md`. Commit by explicit paths. Branch `wh3-team-report` edits `battle/export.py:54-298`, not the terms text.
- Order: check `docs/state.md` (nothing ran at planning time); code and tests in one commit after `scripts/check.py`; ledger files and the live test; docs, references and the log entry in a second commit; a memory note with the key file's path, never its contents.

## Sources (live, read 2026-10-31; add to docs/references.md)

- Versioning, latest `2026-10-21`: https://platform.claude.com/docs/en/api/versioning
- Authentication (Bearer primary, `x-api-key` legacy, workspace scoping, expiry presets): https://platform.claude.com/docs/en/manage-claude/authentication
- Structured outputs (shape, limits of 16 union-typed and 24 optional parameters, enum capitalization, grammar compiled on first use and cached 24 h): https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- Effort: https://platform.claude.com/docs/en/build-with-claude/effort ; thinking and display: https://platform.claude.com/docs/en/build-with-claude/thinking
- Messages reference (usage fields; the example reply is placeholder data): https://platform.claude.com/docs/en/api/messages/create
- Errors (529, 504, 400 on own spend limit, 429 spend cap, 402): https://platform.claude.com/docs/en/api/errors
- Pricing: https://platform.claude.com/docs/en/about-claude/pricing ; caching opt-in: https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- Refusals and fallbacks: https://platform.claude.com/docs/en/build-with-claude/refusals-and-fallback
- Models API capabilities: https://platform.claude.com/docs/en/api/models/retrieve
- Claude Code and `ANTHROPIC_API_KEY`: https://code.claude.com/docs/en/iam
- Terms: https://www.anthropic.com/legal/commercial-terms (§D.4) ; https://www.anthropic.com/legal/aup (effective Nov 12, 2026)
