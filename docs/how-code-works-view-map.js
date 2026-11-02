"use strict";
// The "Map" view of docs/multi-agent.html: the whole repo in 12 boxes. Hand-written; the rules
// are docs/how-code-works-plan.md sections 2 and 5. Strict JSON inside push( ... ), because
// scripts/check.py and scripts/diagram_files.py read it; keep Prettier's --quote-props preserve
// --trailing-comma none. Each box's "files" are the path prefixes it owns in the file lists.
// The wires' rate texts quote the two example battles' counts: they rest on JUDGEMENT? Example
// battles in scripts/diagram_examples.py.
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
        "A battle plan written as a graph of steps, each pointing to the next by outcome; a model can write or revise one offline, and an optional model can suggest a visible target while it runs (one live probe and one battle so far). A temporary check rejects a written graph whose named initiator cannot attack before contact. graph-view draws a recorded battle's graph and orders, with no game or model call.",
      "command":
        "twwarhammer3 play --policy configured --controller-config FILE ...; to look: twwarhammer3 graph-view JOB --output runs/twwarhammer3/reports/NAME.html",
      "stories": ["methods", "graph", "members"],
      "files": [
        "src/twwarhammer3/battle/graph.py",
        "src/twwarhammer3/battle/graph_author.py",
        "src/twwarhammer3/battle/graph_goals.py",
        "src/twwarhammer3/battle/graph_initiation.py",
        "src/twwarhammer3/battle/graph_view.py",
        "src/twwarhammer3/battle/graph_view_assets/",
        "src/twwarhammer3/battle/skill_contracts.py",
        "configs/twwarhammer3/graphs/",
        "configs/twwarhammer3/graph_goal_prompt.md"
      ],
      "status":
        "agreed live check: WH3 initial GaP, live 3/3 at d12be58 (docs/agreed-checks.md:72-88); target hints passed at 87518f9, one probe (docs/agreed-checks.md:34-58); agreed offline checks: viewer passed at b8f8cb7 (docs/agreed-checks.md:59-71), initiation check passed at 4f0c3fc (docs/agreed-checks.md:18-33)",
      "commit": "ad43a37",
      "refs": [
        "src/twwarhammer3/battle/graph.py:1-6",
        "src/twwarhammer3/battle/graph_author.py:1",
        "src/twwarhammer3/battle/graph_goals.py:1",
        "src/twwarhammer3/battle/graph_initiation.py:1-5",
        "src/twwarhammer3/battle/graph_view.py:1-5",
        "docs/twwarhammer3/gap-plan.md:314-318",
        "docs/twwarhammer3/gap-plan.md:349-352",
        "docs/twwarhammer3/gap-plan.md:369-376",
        "docs/twwarhammer3/gap-plan.md:403-405",
        "docs/twwarhammer3/gap-plan.md:437-448",
        "docs/agreed-checks.md:18-33",
        "docs/agreed-checks.md:34-58",
        "docs/agreed-checks.md:59-71",
        "docs/agreed-checks.md:72-88"
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
      "stories": ["job", "methods", "decision", "members"],
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
      ],
      "stories": ["decision"]
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
      "rate": {
        "kind": "job",
        "short": "once a job",
        "text":
          "A job that starts the game runs the scenario's lobby steps once; its later battles restart the same battle. A job with --attach joins the battle already running."
      },
      "refs": [
        "src/twwarhammer3/battle/setup.py:1-3",
        "src/twwarhammer3/battle/play.py:1-5",
        "src/twwarhammer3/battle/play.py:174-187",
        "src/twwarhammer3/battle/play.py:201"
      ]
    },
    {
      "id": "map.factory>play",
      "from": "map.factory",
      "to": "map.play",
      "label": "starts jobs",
      "payload": "An agent or the queue starts a play job with a command line.",
      "status": "built, component tests only",
      "rate": {
        "kind": "job",
        "short": "a job at a time",
        "text":
          "The queue runs a frozen plan of play jobs one at a time; agents also start single jobs by hand."
      },
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
      "rate": {
        "kind": null,
        "short": "graph jobs only",
        "graph": {"kind": "job", "short": "once a job"},
        "text":
          "A job loads its graphs when it starts; models wrote them before it (3 calls for the 1 Nov battle)."
      },
      "refs": [
        "docs/twwarhammer3/gap-plan.md:358-360",
        "docs/how-code-works-example-methods.js"
      ]
    },
    {
      "id": "map.play>runtime",
      "from": "map.play",
      "to": "map.runtime",
      "label": "orders",
      "bend": -40,
      "payload": "One request at a time, written to orders.json.",
      "status": "built, component tests only",
      "rate": {
        "kind": "seconds",
        "short": "after each decision",
        "graph": {"kind": "fraction", "short": "after each decision"},
        "text":
          "One request after every decision, with or without orders: 88 in the 335 s basic battle of 20 Oct (49 with none) and 2017 in the 618 s GaP battle of 1 Nov (1852 with none). The game reads orders.json every 0.2 s of real time and applies them at its next tick, every 0.25 s of battle time."
      },
      "refs": [
        "src/twwarhammer3/engine/mailbox.py:1",
        "src/twwarhammer3/battle/play.py:724",
        "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:1537",
        "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:1480",
        "docs/how-code-works-example-methods.js"
      ]
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
      "rate": {
        "kind": "second",
        "short": "every 1 s or sooner",
        "graph": {"kind": "fraction", "short": "every 0.3 s"},
        "text":
          "The battle script writes the state every 1 s of battle time (the default --observe-ms) and again after it applies each request; the play loop looks for a new one every 0.1 s. A graph controller sends a request at every view, so in the 618 s GaP battle of 1 Nov the state came every 0.3 s (1990 of 2016 gaps; the other 26 were 0.6 s)."
      },
      "refs": [
        "src/twwarhammer3/engine/mailbox.py:91-92",
        "src/twwarhammer3/protocol.py:45",
        "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:283-289",
        "src/twwarhammer3/__main__.py:26-27",
        "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:1331-1334",
        "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:1130",
        "src/twwarhammer3/engine/mailbox.py:173",
        "docs/how-code-works-example-methods.js"
      ]
    },
    {
      "id": "map.checkpoints>runtime",
      "from": "map.checkpoints",
      "to": "map.runtime",
      "label": "save, rebuild",
      "payload": "Saves a battle mid-way and rebuilds it from the saved tick.",
      "status": "built, component tests only",
      "rate": {
        "kind": "job",
        "short": "per checkpoint run",
        "text":
          "A checkpoint run plays one source battle or one restore through the normal harness."
      },
      "refs": [
        "src/twwarhammer3/battle/checkpoint.py:1",
        "src/twwarhammer3/battle/checkpoint.py:10-11"
      ]
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
      "rate": {
        "kind": "seconds",
        "short": "every few seconds",
        "graph": {"kind": null, "short": "none, or a few hints"},
        "text":
          "A model controller asks at every decision: 92 calls in the 335 s battle of 20 Oct (88 decisions, 3 re-asks after a refused batch and 1 call still out at the end), and its orders used a view 3.3 s old (median). The graph controllers of the 1 Nov battle asked none during it; a graph with target hints asks at most once every 30 s of battle while it sees candidate targets, up to its request cap (rests on JUDGEMENT G4 Goal limits in graph_goals.py)."
      },
      "refs": [
        "src/gameai/llm.py:1",
        "docs/how-code-works-example-methods.js",
        "src/twwarhammer3/battle/graph_goals.py:24-27",
        "src/twwarhammer3/battle/graph_goals.py:207-212"
      ]
    },
    {
      "id": "map.models>provider",
      "from": "map.models",
      "to": "map.provider",
      "label": "requests",
      "payload": "HTTPS requests to the provider the job named.",
      "status": "outside our code: the provider APIs (src/gameai/providers.py:92)",
      "rate": {
        "kind": "seconds",
        "short": "per model call",
        "graph": {"kind": null, "short": "per model call"},
        "text":
          "One HTTPS request per model call, more when the service has a passing failure."
      },
      "refs": [
        "src/gameai/providers.py:92",
        "src/gameai/llm.py:1",
        "src/gameai/llm.py:133-136"
      ]
    },
    {
      "id": "map.play>reports",
      "from": "map.play",
      "to": "map.reports",
      "label": "trace, result, results.csv row",
      "payload":
        "Each episode's trace.jsonl and result.json, and one row in docs/twwarhammer3/results.csv.",
      "status": "built, component tests only",
      "rate": {
        "kind": "battle",
        "short": "once a battle",
        "text":
          "trace.jsonl grows during the battle; result.json and the results.csv row are written once, when it ends. The two example battles lasted 335 s and 618 s."
      },
      "refs": [
        "src/twwarhammer3/battle/stats.py:1-3",
        "src/twwarhammer3/battle/play.py:161",
        "docs/how-code-works-example-methods.js"
      ]
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
