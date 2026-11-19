"use strict";
// The "Map" view of docs/how-code-works.html: the WH3 code in 11 boxes. Hand-written; the rules
// are docs/how-code-works-plan.md sections 2 and 5. Strict JSON inside push( ... ), because
// scripts/check.py and scripts/diagram_files.py read it; keep Prettier's --quote-props preserve
// --trailing-comma none. Each box's "files" are the path prefixes it owns in the file lists;
// "outside" lists Slay the Spire's, which the page leaves out (owner, 2026-11-01: "omit that game
// and make it clear that we're talking about only WH3").
// The wires' rate texts quote the two example battles' counts: they rest on JUDGEMENT? Example
// battles in scripts/diagram_examples.py.
DIAGRAM.tabs.push({
  "id": "map",
  "title": "Map",
  "question": "What are the parts of the WH3 code, and how do they connect?",
  "takeaway":
    "A WH3 play job runs one battle at a time in the real game; most other parts prepare, check or read those battles. Slay the Spire, the repo's other game, is not drawn.",
  "summary":
    "Eleven areas, in the bands where they run. Click a box for what it does, the command that starts it, its stories and its files.",
  "banner":
    "The full-map review date below is 1 Nov. Status lines were source-reviewed on 4 Nov, and the file lists and flagged references on 14 Nov; historical rate examples keep their original dates.",
  "commit": "7bf32e6",
  "reviewed": "2026-11-01",
  "facts": {
    "providers": ["openai", "openrouter", "anthropic"],
    "hidden_keys": ["evaluation", "final", "setup", "native"]
  },
  "outside": [
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
      "commit": "601d249",
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
        "agreed offline check: WH3 UI requests and mailbox requests (docs/agreed-checks.md:231, 239)",
      "refs": [
        "src/twwarhammer3/engine/mailbox.py:1",
        "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:1-6",
        "src/gameai/windows.py",
        "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:328-334",
        "docs/agreed-checks.md:231-234",
        "docs/agreed-checks.md:239-242"
      ]
    },
    {
      "id": "map.setup",
      "commit": "601d249",
      "label": "Scenarios and setup",
      "code": "battle/setup.py · scenarios/",
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
        "src/twwarhammer3/controllers/calibration.py",
        "src/twwarhammer3/battle/reserve.py",
        "configs/twwarhammer3/scenarios/",
        "configs/twwarhammer3/custom_battle.json"
      ],
      "status": "agreed live check: WH3 saved armies and experience (docs/agreed-checks.md:221)",
      "refs": [
        "src/twwarhammer3/battle/setup.py:1",
        "configs/twwarhammer3/scenarios/",
        "docs/agreed-checks.md:221-230"
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
        "A battle plan written as a graph of steps, each pointing to the next by outcome; a model can write or revise one offline, and an optional model can suggest a visible target while it runs. A temporary check rejects a written graph whose named initiator cannot attack before contact. graph-view draws a recorded battle's graph and orders, with no game or model call.",
      "command":
        "twwarhammer3 play --policy configured --controller-config FILE ...; to look: twwarhammer3 graph-view JOB --output runs/twwarhammer3/reports/NAME.html",
      "stories": ["methods", "graph", "members"],
      "files": [
        "src/twwarhammer3/controllers/graph.py",
        "src/twwarhammer3/controllers/graph_author.py",
        "src/twwarhammer3/controllers/graph_goals.py",
        "src/twwarhammer3/controllers/graph_initiation.py",
        "src/twwarhammer3/results/graph_view.py",
        "src/twwarhammer3/results/graph_view_assets/",
        "src/twwarhammer3/controllers/skill_contracts.py",
        "configs/twwarhammer3/graphs/",
        "configs/twwarhammer3/graph_goal_prompt.md"
      ],
      "status":
        "agreed live check: WH3 initial GaP, live 3/3 at d12be58 (docs/agreed-checks.md:170-186); target hints passed at 87518f9, one probe (docs/agreed-checks.md:132-156); agreed offline checks: viewer passed at b8f8cb7 (docs/agreed-checks.md:157-169), initiation check passed at 4f0c3fc (docs/agreed-checks.md:116-131)",
      "commit": "601d249",
      "refs": [
        "src/twwarhammer3/controllers/graph.py:1-6",
        "src/twwarhammer3/controllers/graph_author.py:1",
        "src/twwarhammer3/controllers/graph_goals.py:1",
        "src/twwarhammer3/controllers/graph_initiation.py:1-5",
        "src/twwarhammer3/results/graph_view.py:1-5",
        "docs/twwarhammer3/gap-plan.md:320-324",
        "docs/twwarhammer3/gap-plan.md:355-358",
        "docs/twwarhammer3/gap-plan.md:375-382",
        "docs/twwarhammer3/gap-plan.md:409-411",
        "docs/twwarhammer3/gap-plan.md:443-454",
        "docs/agreed-checks.md:116-131",
        "docs/agreed-checks.md:132-156",
        "docs/agreed-checks.md:157-169",
        "docs/agreed-checks.md:170-186"
      ]
    },
    {
      "id": "map.posttraining",
      "commit": "601d249",
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
        "Turns WH3's exported model decisions into fine-tuning datasets (the same code reads Slay the Spire's). Only smoke tests have run on WH3 data; there is no WH3 learning result.",
      "command": "uv run --locked --extra llm python scripts/sft_smoke.py DATASET --output DIR",
      "files": ["src/gameai/sft.py", "scripts/sft_smoke.py"],
      "status": "built, component tests only",
      "refs": ["src/gameai/sft.py:1", "scripts/sft_smoke.py:1", "docs/state.md:74"]
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
        "src/twwarhammer3/controllers/factory.py",
        "src/twwarhammer3/controllers/llm.py",
        "src/twwarhammer3/controllers/commander.py",
        "src/twwarhammer3/controllers/skills.py",
        "src/twwarhammer3/controllers/scripted.py",
        "src/twwarhammer3/controllers/reference.py",
        "src/twwarhammer3/controllers/team.py",
        "src/twwarhammer3/controllers/configured.py",
        "src/twwarhammer3/battle/cannae.py",
        "src/twwarhammer3/controllers/evade.py",
        "src/twwarhammer3/controllers/local_command.py",
        "src/twwarhammer3/controllers/local_team.py",
        "src/twwarhammer3/battle/support_timing.py",
        "src/twwarhammer3/battle/manual_demo.py",
        "src/twwarhammer3/scenarios/wall_defence.py",
        "src/twwarhammer3/battle/escalade.py",
        "src/twwarhammer3/scenarios/evidence_rules.py",
        "src/twwarhammer3/scenarios/camp_facts.py",
        "src/twwarhammer3/scenarios/lines_facts.py",
        "src/twwarhammer3/scenarios/wall_facts.py",
        "src/twwarhammer3/battle/escalade_facts.py",
        "src/twwarhammer3/units.py",
        "src/twwarhammer3/order_text.py",
        "src/twwarhammer3/policy_names.py",
        "src/twwarhammer3/scope.py",
        "src/twwarhammer3/scenarios/support_facts.py",
        "src/twwarhammer3/scenarios/camp.py",
        "src/twwarhammer3/scenarios/lines.py",
        "src/twwarhammer3/battle/local_scripts.py",
        "src/twwarhammer3/controllers/replay_schedule.py",
        "configs/twwarhammer3/system_prompt.md",
        "configs/twwarhammer3/rules_prompt.md",
        "configs/twwarhammer3/commander_prompt.md",
        "configs/twwarhammer3/tips_prompt.md",
        "configs/twwarhammer3/local_command_prompt.md",
        "configs/twwarhammer3/cannae_shared_plan.md",
        "configs/twwarhammer3/cannae_shared_plan_v2.md",
        "configs/twwarhammer3/local_captain_prompt.md",
        "configs/twwarhammer3/local_commander_prompt.md",
        "configs/twwarhammer3/local_topology_rules.json",
        "configs/twwarhammer3/controllers/"
      ],
      "status":
        "agreed live check: scripted team; direct model-team mechanics passed one declared case at c1ad84d. Strength remains unverified",
      "commit": "601d249",
      "refs": [
        "src/twwarhammer3/battle/play.py:1",
        "src/twwarhammer3/controllers/factory.py:1",
        "src/twwarhammer3/protocol.py:47",
        "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:328-332",
        "docs/agreed-checks.md:191-220"
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
        "Each episode appends one results.csv row. digest and report read recorded files, and stats reads results.csv. benchmark and suite declare planned attempts, enforce their limits around live jobs, and measure and report the recorded results.",
      "command": "uv run python -m twwarhammer3 report JOB --output runs/twwarhammer3/reports/NAME",
      "stories": ["job"],
      "files": [
        "src/twwarhammer3/battle/support_evidence.py",
        "src/twwarhammer3/scenarios/wall_readings.py",
        "src/twwarhammer3/battle/escalade_readings.py",
        "src/twwarhammer3/scenarios/camp_readings.py",
        "src/twwarhammer3/scenarios/lines_readings.py",
        "src/twwarhammer3/scenarios/evidence_rules.py",
        "src/twwarhammer3/scenarios/camp_facts.py",
        "src/twwarhammer3/scenarios/lines_facts.py",
        "src/twwarhammer3/scenarios/wall_facts.py",
        "src/twwarhammer3/battle/escalade_facts.py",
        "src/twwarhammer3/units.py",
        "src/twwarhammer3/order_text.py",
        "src/twwarhammer3/policy_names.py",
        "src/twwarhammer3/scope.py",
        "src/twwarhammer3/scenarios/support_facts.py",
        "src/twwarhammer3/benchmarks/exact_stats.py",
        "src/twwarhammer3/benchmarks/profile.py",
        "src/twwarhammer3/benchmarks/plans.py",
        "src/twwarhammer3/benchmarks/suite.py",
        "src/twwarhammer3/results/report.py",
        "src/twwarhammer3/results/report_html.py",
        "src/twwarhammer3/results/replay.py",
        "src/twwarhammer3/results/report_assets/",
        "src/twwarhammer3/results/register.py",
        "src/twwarhammer3/results/digest.py",
        "src/twwarhammer3/results/watch.py",
        "src/twwarhammer3/results/export.py",
        "src/twwarhammer3/battle/capture.py",
        "scripts/wh3_reserve_cells.py",
        "src/twwarhammer3/results/report_assets/report_notes.json",
        "configs/twwarhammer3/benchmark_jobs.json"
      ],
      "status": "built, component tests only",
      "commit": "fd37495",
      "refs": [
        "src/twwarhammer3/results/register.py:1-3",
        "src/twwarhammer3/results/report.py:1",
        "docs/twwarhammer3/results.csv",
        "src/twwarhammer3/benchmarks/profile.py:1-5",
        "src/twwarhammer3/benchmarks/plans.py:1-6",
        "src/twwarhammer3/benchmarks/suite.py:1-11"
      ]
    },
    {
      "id": "map.checkpoints",
      "label": "Checkpoints and RL",
      "code": "checkpoint/checkpoint.py · rl.py",
      "kind": "process",
      "where": "WSL Python",
      "x": 800,
      "y": 130,
      "w": 230,
      "h": 64,
      "state": "runs today",
      "note":
        "Saves a running battle at a tick, then replays its inputs to that tick before returning live control. The checkpoint-RL experiment built on it is paused.",
      "command": "uv run --locked python tests/twwarhammer3/check_wh3_checkpoint.py --output DIR",
      "files": [
        "src/twwarhammer3/checkpoint/checkpoint.py",
        "src/twwarhammer3/checkpoint/candidates.py",
        "src/twwarhammer3/checkpoint/audit.py",
        "src/twwarhammer3/checkpoint/rl.py",
        "src/twwarhammer3/checkpoint/confirm.py",
        "src/twwarhammer3/checkpoint/checkpoint_agent.js",
        "src/twwarhammer3/checkpoint/checkpoint_frida.py",
        "src/gameai/lm.py"
      ],
      "status":
        "agreed live check: Land and siege live-value checks passed for their declared states and readings; other states remain unverified (docs/twwarhammer3/checkpoints.md)",
      "commit": "601d249",
      "refs": [
        "src/twwarhammer3/checkpoint/checkpoint.py:1",
        "src/twwarhammer3/checkpoint/rl.py:1",
        "docs/twwarhammer3/checkpoints.md:1-14",
        "docs/agreed-checks.md:247-285",
        "docs/agreed-checks.md:287-312"
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
      "ran": true,
      "state": "ran, unverified",
      "note":
        "Each game client has a worker, joined by a coordinator. PC-hosted battles with a VM peer are recorded; full control remains unverified.",
      "command": "uv run python -m twwarhammer3 coordinator --match M --attempt A1 --clients A,B",
      "files": [
        "src/twwarhammer3/multiplayer/link.py",
        "src/twwarhammer3/multiplayer/worker.py",
        "src/twwarhammer3/multiplayer/peers.py",
        "scripts/wh3_gcp.py",
        "scripts/gcp/",
        "configs/twwarhammer3/gcp-regions.json"
      ],
      "status": "built, unverified",
      "commit": "601d249",
      "refs": [
        "src/twwarhammer3/multiplayer/worker.py:1-3",
        "src/twwarhammer3/multiplayer/peers.py:1-3",
        "docs/twwarhammer3/log.md:1684-1707"
      ]
    },
    {
      "id": "map.models",
      "commit": "601d249",
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
        "agreed offline check: play commands refuse a missing ledger file (docs/agreed-checks.md:235)",
      "refs": [
        "src/gameai/llm.py:1",
        "src/gameai/ledger.py:1",
        "src/gameai/providers.py:92",
        "docs/agreed-checks.md:235-238"
      ],
      "stories": ["decision"]
    },
    {
      "id": "map.provider",
      "commit": "108b3e6",
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
      "refs": ["src/gameai/providers.py:92", "docs/twwarhammer3/README.md:458-464"]
    }
  ],
  "wires": [
    {
      "id": "map.setup>play",
      "commit": "601d249",
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
        "src/twwarhammer3/battle/setup.py:1",
        "src/twwarhammer3/battle/play.py:1-5",
        "src/twwarhammer3/battle/play.py:219-233",
        "src/twwarhammer3/battle/play.py:248"
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
      "commit": "601d249",
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
        "docs/twwarhammer3/gap-plan.md:409-411",
        "docs/how-code-works-example-methods.js"
      ]
    },
    {
      "id": "map.play>runtime",
      "commit": "601d249",
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
        "src/twwarhammer3/battle/play.py:890",
        "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:2369",
        "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:2312",
        "docs/how-code-works-example-methods.js"
      ]
    },
    {
      "id": "map.runtime>play",
      "commit": "601d249",
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
        "src/twwarhammer3/engine/mailbox.py:117-118",
        "src/twwarhammer3/protocol.py:47",
        "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:328-334",
        "src/twwarhammer3/__main__.py:26-27",
        "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:2125-2137",
        "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:1838",
        "src/twwarhammer3/engine/mailbox.py:209",
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
        "src/twwarhammer3/checkpoint/checkpoint.py:1",
        "src/twwarhammer3/checkpoint/checkpoint.py:10-11"
      ]
    },
    {
      "id": "map.multiplayer>runtime",
      "from": "map.multiplayer",
      "to": "map.runtime",
      "label": "a worker per client",
      "payload": "Each worker reads and writes one game client's files.",
      "status": "built, unverified",
      "refs": ["src/twwarhammer3/multiplayer/worker.py:1-3"]
    },
    {
      "id": "map.play>models",
      "from": "map.play",
      "to": "map.models",
      "label": "model calls",
      "payload": "The direct model controller in the dated example asks for orders. Commander and graph target hints use other timings.",
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
        "src/twwarhammer3/controllers/graph_goals.py:24-27",
        "src/twwarhammer3/controllers/graph_goals.py:207-212"
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
      "commit": "601d249",
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
        "src/twwarhammer3/results/register.py:1-3",
        "src/twwarhammer3/battle/play.py:198",
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
    }
  ]
});
