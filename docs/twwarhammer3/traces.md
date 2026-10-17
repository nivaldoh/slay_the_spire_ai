# Model trace exports

`export` reads saved WH3 jobs or episodes and writes a dataset for future post-training
and analysis. It makes no API calls, launches no game and never changes source evidence.
It does not train a model or declare the data suitable for a particular training use.

```bash
uv run python -m twwarhammer3 export runs/twwarhammer3/battle/JOB \
    --output runs/twwarhammer3/exports/NAME
uv run python -m twwarhammer3 export --jobs-file configs/twwarhammer3/benchmark_jobs.json \
    --prompt-version v20 --output runs/twwarhammer3/exports/v20
```

Positional paths accept jobs or individual `episode-NNNN` directories. A jobs file is a
JSON list of paths relative to the working directory, as with `report`. Duplicate
selections are deduplicated. The destination must be new and outside the source jobs.
Jobs still marked running and episodes without `result.json` are refused. Truncated or
failed episodes with saved results are included with their original statuses.

Filters `--prompt-version`, `--model` and `--prompt-sha256` are repeatable. Values within
one filter are alternatives; different filters must all match. `--prompt-version unknown`
selects historical episodes without a version label. An exact prompt hash also works
when the human-readable version was not recorded. All selections and exclusions appear
in the source inventory. Outputs are deterministic for unchanged inputs and exporter code.

## Files and schema

- `decisions.jsonl`: one JSON object per model request, with all its reply attempts.
- `sources.json`: source manifests, environments, results, file hashes, filters, coverage
  (rows by split, group and provider), exporter/measures code hashes and the hash of
  `decisions.jsonl`.
- `datacard.md`: a generated data card documenting the specific export and its limitations.

Rows follow the export-row contract both games' exporters share (schema 2): a dataset
builder reads only `schema_version`, `id`, `game`, `group`, `split`, policy, provider,
model, effort, `prompt_version`, the system and user prompts with their hashes,
`attempts`, `error`, `outcome`, `labels` and `provenance`. Everything else in a row is
WH3 detail. Its fine-tuning target is a row's last attempt, and only when that attempt has
no error, status `completed` and non-empty text, the row's `error` is null and its
`split` is `development`. `id` is `<source id>/<episode>/m<decision index>`; the source
id is the SHA-256 of the job directory name, a newline and the manifest's SHA-256, so ids
and row bytes do not depend on where the evidence is stored (`sources[].path` still
records it). Rows follow the job names, and selecting one job from two locations is an
error.
`provenance` names the source id, episode, source revision, controller card,
trace/result hashes and the trace lines of the prompt and model exchange. Source
manifests preserve the full configuration, source-file fingerprints, engine build,
deployment and mod hashes; missing historical environment data remains null.

| Field | Meaning |
|---|---|
| `game`, `group`, `split` | `twwarhammer3`; the unit to keep whole when splitting; `development` or `held_out` (below) |
| `system_prompt`, `user_prompt` | Saved system instructions and initial user prompt, without rerendering or trimming |
| `attempts` | Every saved raw reply attempt in request order, including invalid replies, usage, cost and recorded timing/backend fields |
| `attempts[].user_prompt` | That attempt's exact user prompt, including its retry feedback |
| `attempts[].text`, `status`, `error` | Raw reply and provider status (null after a transport failure); null error for the accepted reply, else the parser's, transport's or failed request's message |
| `attempts[].prompt_source` | Recorded request, saved initial prompt, verified historical retry reconstruction, or unavailable |
| `attempts[].request`, `output` | New traces: exact request body (including schema) and returned output items |
| `attempts[].reasoning` | Returned text parts, preserving summary/content type and position; null when unavailable |
| `decision_metadata` | Saved reason, notes, adopted plan, dropped orders and other controller metadata |
| `execution` | Submitted order batches, validation failures, engine acknowledgements and latency |
| `error` | Null when the request ended with an accepted reply, else `{"type", "message"}` |
| `outcome` | Original status, gameplay outcome, final measurements and common report measures |
| `labels` | Scenario, battle type, added delay, locally rejected batches and engine-refused orders |
| `issues` | Explicit gaps such as a missing prompt, reply or acknowledgement |

`group` is the declared scenario family (`manifest.scenario.family`), else the scenario
name. A random scenario draws a new battle per seed and jobs can repeat a seed (paired
controllers), so its group is `<scenario>/seed-<seed>`, or the job directory name if no
seed was recorded. `split` is `held_out` only for a scenario declared
`"split": "held_out"`. Held-out variants inherit their family from development
scenarios, so the split, not the group, keeps them out of training. Variants that share a
`base` but declare no family get one group each; declare a family in `scenarios.json` to
keep them together. `labels` count batches and refusals over the row's `execution`, which
for commander includes later executor ticks; `battle_type` is `classic` unless the
scenario declares another, as in `stats`.

A salvaged llm reply (its still-valid orders kept after every retry failed) has the error
`{"type": "InvalidReply", ...}`: new traces record it in the exchange, and for older
traces, whose decisions record the dropped orders but not the error, its message is null.

Schema 2 changed from schema 1: rows gained `game`, `group`, `split` and `labels`; ids no
longer hash the absolute job path; `error` is always present, and the old string failure
kind became `{"type": kind, "message": <the result's error>}`; attempts always carry
`text`, `status`, `usage` and `error`; `attempts[].system_prompt` is gone (it repeated the
row's `system_prompt`, about a fifth of the first full export); `prompt_trace_line` and
`exchange_trace_line` moved into `provenance`. Each recorded request's instructions are
still checked against the saved system prompt; a job without a saved prompt file takes
the instructions of its recorded requests, which must agree.

The catalog retains full results, including measurements not repeated in each row.
Only `won`, `lost` and `draw` populate `outcome.gameplay_outcome`. Policy/infrastructure
failures, interruptions, budget stops and truncations are not losses. Evaluation-only
measurements stay in outcome/source fields and must never be appended to policy inputs.

## Historical and asynchronous traces

A direct controller's reply answers the prompt beside it. A commander's reply answers
its previous request: the next prompt can be logged on the same executor tick as the
previous reply. The exporter associates them accordingly. Commander execution spans
adoption through the next adoption, including later logged executor ticks. Standing
assignments can persist from still earlier plans; these are hybrid-controller actions.
Default-skill ticks before the first plan are counted but not attributed to the model.

An empty order batch differs from missing execution; an empty acknowledgement differs
from a missing acknowledgement. Engine refusals, locally rejected batches, salvaged
replies and dropped orders are preserved. An episode win does not make every attempt
or order in that episode a correct training target.

Old traces retained the initial prompt and parser errors, but not each retry's request.
The exporter checks the recorded revision and transport-source hash before reconstructing
the known retry suffix. Without that evidence it leaves the retry prompt null. It never
loads today's prompt template to fill a gap. Older single-policy jobs use their saved
`system_prompt.md`; newer jobs use `<policy>_prompt.md`. Recorded prompt hashes are checked.
Version labels come from controller cards, or explicitly labelled historical job names.

Before exchange capture, a commander's last paid reply could finish during shutdown and
never enter the trace; a failed direct decision could retain attempts without its prompt.
Those gaps remain explicit. Recorded reasoning-token counts cannot recover reasoning text.

## Capture for future battles

Since harness b14, WH3 opts into model-exchange capture. Completed calls are drained on
the controller thread after decisions and again after shutdown, retaining failed requests
and late, unadopted plans. Each attempt includes its request body and returned output
items; authorization headers and credentials are never recorded. A hard process crash
can still lose an in-flight exchange. HTTP transport retries retain counts and errors,
not responses the client never received.

For OpenAI reasoning modes, capture requests `reasoning.summary: auto`; returned summaries
are not full reasoning ([OpenAI documentation](https://developers.openai.com/api/docs/guides/reasoning)).
For OpenRouter it preserves returned reasoning output without adding a new routing
requirement ([Responses reasoning](https://openrouter.ai/docs/api_reference/responses/reasoning)).
An empty reasoning list means the response was captured but contained no visible text;
null means it was unavailable. Raw encrypted items remain opaque. Reasoning is never
fed back into prompts. Capture is off by default in shared `gameai.Model`; Spire full runs
opted in on 2026-10-17 (`87b370b`), so their traces gain the same events and their OpenAI
requests ask for summaries too. Controller prompts remain v20/v7;
`manifest.model_exchange_version: 1` and source revisions identify the capture change.
The capture request setting is offline-tested; no new paid API call was used to validate it.

Before training or redistribution, review the source provider/model terms for the actual
intended use, including restrictions on training competing models. Until the owner decides,
rows produced by OpenAI models stay out of training sets by default; rows from open-weight
models served through OpenRouter may enter them. The export is not a training license.
The evidence includes tuning battles, rematches and repeated scenario variants; split by
`group` to avoid leakage. It is not a curated expert-demonstration dataset.
