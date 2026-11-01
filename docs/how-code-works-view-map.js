"use strict";
// The "Map" view of docs/multi-agent.html: the whole repo in 12 boxes. Hand-written; the rules
// are docs/how-code-works-plan.md sections 2 and 5. Strict JSON inside push( ... ), because
// scripts/check.py and scripts/diagram_files.py read it; keep Prettier's --quote-props preserve
// --trailing-comma none. Each box's "files" are the path prefixes it owns in the file lists.
DIAGRAM.tabs.push({
  "id": "map",
  "title": "Map",
  "question": "What are the parts of this repo, and how do they connect?",
  "takeaway":
    "A WH3 play job runs one battle at a time in the real game; most other parts prepare, check or read those battles.",
  "summary":
    "Twelve areas, in the bands where they run. Click a box for what it does, the command that starts it, its stories and its files.",
  "commit": "7bf32e6",
  "reviewed": "2026-11-01",
  "facts": {
    "providers": ["openai", "openrouter", "anthropic"],
    "hidden_keys": ["evaluation", "final", "setup", "native"]
  },
  "size": [1060, 572],
  "bands": [
    {
      "where": "Windows game",
      "x": 0,
      "y": 0,
      "w": 1060,
      "h": 96
    },
    {
      "where": "WSL Python",
      "x": 0,
      "y": 104,
      "w": 1060,
      "h": 398
    },
    {
      "where": "cloud API",
      "x": 0,
      "y": 508,
      "w": 1060,
      "h": 64
    }
  ],
  "elements": [
    {
      "id": "map.runtime",
      "label": "The game and our Lua scripts",
      "code": "engine/ · mod/",
      "kind": "process",
      "where": "Windows game",
      "x": 330,
      "y": 22,
      "w": 400,
      "h": 60,
      "state": "runs today",
      "note":
        "Warhammer3.exe runs our Lua scripts. In a battle they write observation.json, with enemy units only while our side can see them, and apply the orders found in orders.json.",
      "command": "uv run python -m twwarhammer3 launch (or a play job)",
      "stories": ["job"],
      "files": [
        "src/twwarhammer3/engine/",
        "src/twwarhammer3/mod/",
        "src/twwarhammer3/assets/",
        "src/gameai/windows.py",
        "src/gameai/windows_game.py",
        "scripts/wh3_db.py"
      ],
      "status":
        "agreed offline check: WH3 UI requests and mailbox requests (docs/agreed-checks.md:71, 79)",
      "refs": [
        "src/twwarhammer3/engine/mailbox.py:1",
        "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:1-6",
        "src/gameai/windows.py",
        "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:283-289",
        "docs/agreed-checks.md:71-74",
        "docs/agreed-checks.md:79-82"
      ]
    },
    {
      "id": "map.setup",
      "label": "Scenarios and setup",
      "code": "battle/setup.py · scenarios.json",
      "kind": "process",
      "where": "WSL Python",
      "x": 30,
      "y": 130,
      "w": 230,
      "h": 64,
      "state": "runs today",
      "note":
        "A scenario names the armies, the map and the rules. Setup clicks through the custom battle screen and checks that the battle matches the scenario.",
      "command": "twwarhammer3 play --scenario NAME ...",
      "stories": ["job"],
      "files": [
        "src/twwarhammer3/battle/setup.py",
        "src/twwarhammer3/battle/calibration.py",
        "src/twwarhammer3/battle/cards.py",
        "configs/twwarhammer3/scenarios.json",
        "configs/twwarhammer3/custom_battle.json"
      ],
      "status": "agreed live check: WH3 saved armies and experience (docs/agreed-checks.md:61)",
      "refs": [
        "src/twwarhammer3/battle/setup.py:1-3",
        "configs/twwarhammer3/scenarios.json",
        "docs/agreed-checks.md:61-70"
      ]
    },
    {
      "id": "map.factory",
      "label": "Development factory",
      "code": "check.py · hooks · wh3_queue.py",
      "kind": "process",
      "where": "WSL Python",
      "x": 30,
      "y": 240,
      "w": 230,
      "h": 64,
      "state": "runs today",
      "note":
        "Agent sessions change the code. check.py runs Ruff and every offline test before each commit; the queue runs a frozen plan of play jobs, one at a time.",
      "command": "uv run --locked python scripts/check.py",
      "files": [
        "scripts/check.py",
        "scripts/githooks/",
        "scripts/hooks/",
        "scripts/wh3_queue.py",
        "scripts/refusal_sweep.py",
        "scripts/diagram_",
        "src/gameai/provenance.py"
      ],
      "status": "built, component tests only",
      "refs": ["scripts/check.py:1", "scripts/wh3_queue.py:1", "docs/workflow.md"]
    },
    {
      "id": "map.graphs",
      "label": "Graph controllers (GaP)",
      "code": "graph*.py · configs/.../graphs/",
      "kind": "process",
      "where": "WSL Python",
      "x": 30,
      "y": 350,
      "w": 230,
      "h": 64,
      "state": "runs today",
      "note":
        "A battle plan written as a graph of steps, each pointing to the next by outcome; a model can write or revise one offline, and an optional model can suggest a visible target while it runs (not yet run live). graph-view draws a recorded battle's graph and orders, with no game or model call.",
      "command":
        "twwarhammer3 play --policy configured --controller-config FILE ...; to look: twwarhammer3 graph-view JOB --output runs/twwarhammer3/reports/NAME.html",
      "files": [
        "src/twwarhammer3/battle/graph.py",
        "src/twwarhammer3/battle/graph_author.py",
        "src/twwarhammer3/battle/graph_goals.py",
        "src/twwarhammer3/battle/graph_view.py",
        "src/twwarhammer3/battle/graph_view_assets/",
        "src/twwarhammer3/battle/skill_contracts.py",
        "configs/twwarhammer3/graphs/",
        "configs/twwarhammer3/graph_goal_prompt.md"
      ],
      "status":
        "agreed live check: WH3 initial GaP, live 3/3 at d12be58 (docs/agreed-checks.md:52, 67); target preferences agreed, live not yet run (docs/agreed-checks.md:18, 38); viewer passed at b8f8cb7 (docs/agreed-checks.md:39, 49)",
      "commit": "87518f9",
      "refs": [
        "src/twwarhammer3/battle/graph.py:1-6",
        "src/twwarhammer3/battle/graph_author.py:1",
        "src/twwarhammer3/battle/graph_goals.py:1",
        "src/twwarhammer3/battle/graph_view.py:1-5",
        "docs/twwarhammer3/gap-plan.md:314-318",
        "docs/twwarhammer3/gap-plan.md:359-361",
        "docs/twwarhammer3/gap-plan.md:393-404",
        "docs/agreed-checks.md:18-38",
        "docs/agreed-checks.md:39-51",
        "docs/agreed-checks.md:52-68"
      ]
    },
    {
      "id": "map.posttraining",
      "label": "Post-training",
      "code": "gameai/sft.py · sft_smoke.py",
      "kind": "process",
      "where": "WSL Python",
      "x": 30,
      "y": 430,
      "w": 230,
      "h": 64,
      "state": "paused",
      "note":
        "Turns recorded model decisions from both games into fine-tuning datasets. Only smoke tests have run; there is no learning result.",
      "command": "uv run --locked --extra llm python scripts/sft_smoke.py DATASET --output DIR",
      "files": ["src/gameai/sft.py", "scripts/sft_smoke.py"],
      "status": "built, component tests only",
      "refs": ["src/gameai/sft.py:1", "scripts/sft_smoke.py:1", "docs/state.md:68"]
    },
    {
      "id": "map.play",
      "label": "Play job and controllers",
      "code": "play.py · llm.py · controllers.py",
      "kind": "process",
      "where": "WSL Python",
      "x": 400,
      "y": 196,
      "w": 260,
      "h": 76,
      "state": "runs today",
      "note":
        "A play job launches the game, sets up one custom battle per episode and lets one controller order our units until the engine reports won, lost or draw. The battle never waits for the model, and a policy never sees enemies its side cannot see.",
      "command": "uv run python -m twwarhammer3 play --scenario S --policy P --output runs/...",
      "stories": ["job"],
      "files": [
        "src/twwarhammer3/__main__.py",
        "src/twwarhammer3/protocol.py",
        "src/twwarhammer3/battle/play.py",
        "src/twwarhammer3/battle/controllers.py",
        "src/twwarhammer3/battle/llm.py",
        "src/twwarhammer3/battle/commander.py",
        "src/twwarhammer3/battle/skills.py",
        "src/twwarhammer3/battle/scripted.py",
        "src/twwarhammer3/battle/team.py",
        "src/twwarhammer3/battle/configured.py",
        "configs/twwarhammer3/system_prompt.md",
        "configs/twwarhammer3/rules_prompt.md",
        "configs/twwarhammer3/commander_prompt.md"
      ],
      "status":
        "agreed live check: WH3 scripted two-member team (docs/agreed-checks.md:48); no agreed check covers the model controllers",
      "refs": [
        "src/twwarhammer3/battle/play.py:1",
        "src/twwarhammer3/battle/controllers.py:1",
        "src/twwarhammer3/protocol.py:45",
        "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:283-287",
        "docs/agreed-checks.md:48-60"
      ]
    },
    {
      "id": "map.reports",
      "label": "Reports and stats",
      "code": "report*.py · stats.py · digest.py",
      "kind": "process",
      "where": "WSL Python",
      "x": 415,
      "y": 330,
      "w": 230,
      "h": 64,
      "state": "runs today",
      "note":
        "Each episode appends one results.csv row. digest and report read a job's recorded files offline, and stats reads results.csv; they print tables or write an HTML report.",
      "command": "uv run python -m twwarhammer3 report JOB --output runs/twwarhammer3/reports/NAME",
      "stories": ["job"],
      "files": [
        "src/twwarhammer3/battle/report.py",
        "src/twwarhammer3/battle/report_html.py",
        "src/twwarhammer3/battle/replay.py",
        "src/twwarhammer3/battle/report_assets/",
        "src/twwarhammer3/battle/stats.py",
        "src/twwarhammer3/battle/digest.py",
        "src/twwarhammer3/battle/watch.py",
        "src/twwarhammer3/battle/export.py",
        "src/twwarhammer3/battle/capture.py",
        "configs/twwarhammer3/report_notes.json",
        "configs/twwarhammer3/benchmark_jobs.json"
      ],
      "status": "built, component tests only",
      "refs": [
        "src/twwarhammer3/battle/stats.py:1-3",
        "src/twwarhammer3/battle/report.py:1",
        "docs/twwarhammer3/results.csv"
      ]
    },
    {
      "id": "map.spire",
      "label": "Slay the Spire",
      "code": "src/spire/",
      "kind": "process",
      "where": "WSL Python",
      "x": 415,
      "y": 430,
      "w": 230,
      "h": 64,
      "state": "paused",
      "note":
        "The second game, paused behind WH3: full runs in which a model makes every choice of a run, through the same model-call code.",
      "command": "uv run python -m spire play ...",
      "files": [
        "src/spire/",
        "configs/llm/",
        "configs/suites/",
        "tests/spire/",
        "docs/spire/",
        "scripts/inventory_scenarios.py",
        "scripts/audit_language_training.py",
        "scripts/audit_ppo_training.py",
        "scripts/export_relabel_datasets.py",
        "scripts/offline_agreement.py",
        "scripts/plot_results.py",
        "scripts/train_language.py",
        "scripts/train_language_rl.py"
      ],
      "status": "built, component tests only",
      "refs": ["src/spire/__init__.py:1", "docs/state.md:57"]
    },
    {
      "id": "map.checkpoints",
      "label": "Checkpoints and RL",
      "code": "battle/checkpoint.py · rl.py",
      "kind": "process",
      "where": "WSL Python",
      "x": 800,
      "y": 130,
      "w": 230,
      "h": 64,
      "state": "runs today",
      "note":
        "Saves a running battle at a tick and rebuilds it later from that tick. The checkpoint-RL experiment built on it is paused.",
      "command": "uv run --locked python tests/twwarhammer3/check_wh3_checkpoint.py --output DIR",
      "files": [
        "src/twwarhammer3/battle/checkpoint.py",
        "src/twwarhammer3/battle/candidates.py",
        "src/twwarhammer3/battle/audit.py",
        "src/twwarhammer3/battle/rl.py",
        "src/twwarhammer3/battle/confirm.py",
        "src/twwarhammer3/engine/checkpoint_agent.js",
        "src/twwarhammer3/engine/checkpoint_frida.py",
        "src/gameai/lm.py"
      ],
      "status":
        "agreed live check: WH3 battle checkpoints restore exactly (docs/agreed-checks.md:87)",
      "refs": [
        "src/twwarhammer3/battle/checkpoint.py:1",
        "src/twwarhammer3/battle/rl.py:1",
        "docs/agreed-checks.md:87-105"
      ]
    },
    {
      "id": "map.multiplayer",
      "label": "Native multiplayer",
      "code": "link.py · worker.py · peers.py",
      "kind": "process",
      "where": "WSL Python",
      "x": 800,
      "y": 240,
      "w": 230,
      "h": 64,
      "ran": false,
      "state": "built, never run",
      "note":
        "Two game clients, one worker beside each, joined by a coordinator, so two controllers can share one real multiplayer battle. No multiplayer battle has run.",
      "command": "uv run python -m twwarhammer3 coordinator --match M --attempt A1 --clients A,B",
      "files": [
        "src/twwarhammer3/engine/link.py",
        "src/twwarhammer3/engine/worker.py",
        "src/twwarhammer3/battle/peers.py"
      ],
      "status": "built, unverified",
      "refs": [
        "src/twwarhammer3/engine/worker.py:1-3",
        "src/twwarhammer3/battle/peers.py:1-3",
        "docs/state.md:51-53"
      ]
    },
    {
      "id": "map.models",
      "label": "Model calls and budget",
      "code": "gameai/llm.py · ledger.py",
      "kind": "process",
      "where": "WSL Python",
      "x": 800,
      "y": 350,
      "w": 230,
      "h": 64,
      "state": "runs today",
      "note":
        "Every model call goes through one module. It first holds the call's worst-case cost in a spend ledger with a hard cap, then sends it to OpenAI, OpenRouter or Anthropic.",
      "command": "a play job with a model policy (--policy llm ...)",
      "files": ["src/gameai/llm.py", "src/gameai/providers.py", "src/gameai/ledger.py"],
      "status":
        "agreed offline check: play commands refuse a missing ledger file (docs/agreed-checks.md:75)",
      "refs": [
        "src/gameai/llm.py:1",
        "src/gameai/ledger.py:1",
        "src/gameai/providers.py:92",
        "docs/agreed-checks.md:75-78"
      ]
    },
    {
      "id": "map.provider",
      "label": "Model providers",
      "code": "OpenAI · OpenRouter · Anthropic",
      "kind": "outside service",
      "where": "cloud API",
      "x": 800,
      "y": 514,
      "w": 230,
      "h": 50,
      "state": "runs today",
      "note": "Outside services, paid per call. Each has its own ledger and cap.",
      "status": "outside our code: the provider APIs (src/gameai/providers.py:92)",
      "refs": ["src/gameai/providers.py:92", "docs/twwarhammer3/README.md:231-236"]
    }
  ],
  "wires": [
    {
      "id": "map.setup>play",
      "from": "map.setup",
      "to": "map.play",
      "label": "scenario",
      "payload": "The scenario's armies, map and checks; play passes them to setup's lobby steps.",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/battle/setup.py:1-3"]
    },
    {
      "id": "map.factory>play",
      "from": "map.factory",
      "to": "map.play",
      "label": "starts jobs",
      "payload": "An agent or the queue starts a play job with a command line.",
      "status": "built, component tests only",
      "refs": ["scripts/wh3_queue.py:1"]
    },
    {
      "id": "map.graphs>play",
      "from": "map.graphs",
      "to": "map.play",
      "label": "a graph as the controller",
      "payload":
        "--policy configured loads a graph controller, which play runs like any other policy.",
      "status": "built, component tests only",
      "refs": ["docs/twwarhammer3/gap-plan.md:358-360"]
    },
    {
      "id": "map.play>runtime",
      "from": "map.play",
      "to": "map.runtime",
      "label": "orders",
      "bend": -40,
      "payload": "One request at a time, written to orders.json.",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/engine/mailbox.py:1"]
    },
    {
      "id": "map.runtime>play",
      "from": "map.runtime",
      "to": "map.play",
      "label": "battle state",
      "bend": -40,
      "payload":
        "observation.json: our units in full, enemy units only while our side can see them. Python then strips the hidden keys (evaluation, final, setup, native) before a policy sees it.",
      "status": "built, component tests only",
      "refs": [
        "src/twwarhammer3/engine/mailbox.py:91-92",
        "src/twwarhammer3/protocol.py:45",
        "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:283-289"
      ]
    },
    {
      "id": "map.checkpoints>runtime",
      "from": "map.checkpoints",
      "to": "map.runtime",
      "label": "save, rebuild",
      "payload": "Saves a battle mid-way and rebuilds it from the saved tick.",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/battle/checkpoint.py:1"]
    },
    {
      "id": "map.multiplayer>runtime",
      "from": "map.multiplayer",
      "to": "map.runtime",
      "label": "a worker per client",
      "payload": "Each worker reads and writes one game client's files.",
      "status": "built, unverified",
      "refs": ["src/twwarhammer3/engine/worker.py:1-3"]
    },
    {
      "id": "map.play>models",
      "from": "map.play",
      "to": "map.models",
      "label": "model calls",
      "payload": "A model controller asks for orders.",
      "status": "built, component tests only",
      "refs": ["src/gameai/llm.py:1"]
    },
    {
      "id": "map.models>provider",
      "from": "map.models",
      "to": "map.provider",
      "label": "requests",
      "payload": "HTTPS requests to the provider the job named.",
      "status": "outside our code: the provider APIs (src/gameai/providers.py:92)",
      "refs": ["src/gameai/providers.py:92"]
    },
    {
      "id": "map.play>reports",
      "from": "map.play",
      "to": "map.reports",
      "label": "trace, result, results.csv row",
      "payload":
        "Each episode's trace.jsonl and result.json, and one row in docs/twwarhammer3/results.csv.",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/battle/stats.py:1-3"]
    },
    {
      "id": "map.reports>posttraining",
      "from": "map.reports",
      "to": "map.posttraining",
      "label": "decision exports",
      "payload": "export writes the recorded model decisions; sft.py turns them into datasets.",
      "status": "built, component tests only",
      "refs": ["src/gameai/sft.py:1"]
    },
    {
      "id": "map.spire>models",
      "from": "map.spire",
      "to": "map.models",
      "label": "model calls",
      "payload": "Spire's full runs use the same model-call module.",
      "status": "built, component tests only",
      "refs": ["src/gameai/llm.py:1"]
    }
  ]
});
