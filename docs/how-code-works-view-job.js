"use strict";
// The "What happens in one play job?" story of docs/multi-agent.html. Hand-written; the rules
// are docs/how-code-works-plan.md sections 2 and 5. Strict JSON inside push( ... ), because
// scripts/check.py and scripts/diagram_examples.py read it; keep Prettier's --quote-props preserve
// --trailing-comma none. Messages and maps come from docs/how-code-works-example-job.js.
DIAGRAM.tabs.push({
  "id": "job",
  "title": "One play job",
  "question": "What happens in one play job?",
  "takeaway":
    "One command launches the game, sets up a custom battle, lets the model order our units until the engine ends it, then writes one results row.",
  "summary":
    "A real battle of 20 Oct: GLM 5.3 commands our Swordsmen and Empire Knights against three Swordsmen, and loses at 335 s.",
  "commit": "7bf32e6",
  "reviewed": "2026-11-01",
  "example": "job",
  "size": [1000, 470],
  "bands": [
    { "where": "Windows game", "x": 0, "y": 0, "w": 1000, "h": 120 },
    { "where": "WSL Python", "x": 0, "y": 128, "w": 1000, "h": 258 },
    { "where": "cloud API", "x": 0, "y": 394, "w": 1000, "h": 76 }
  ],
  "elements": [
    {
      "id": "job.game",
      "label": "The game",
      "code": "Warhammer3.exe",
      "kind": "outside service",
      "where": "Windows game",
      "x": 20,
      "y": 34,
      "w": 180,
      "h": 60,
      "note": "The real game, started by the play job and stopped when the job ends.",
      "status":
        "outside our code: the game, owned by OwnedGame (src/twwarhammer3/battle/play.py:197)",
      "refs": ["src/twwarhammer3/battle/play.py:197", "src/gameai/windows.py"]
    },
    {
      "id": "job.battle",
      "label": "Battle script",
      "code": "twwarhammer3_battle.lua",
      "kind": "process",
      "where": "Windows game",
      "x": 215,
      "y": 34,
      "w": 185,
      "h": 60,
      "note":
        "Our Lua script inside the battle: it writes the state our side can see and applies orders.",
      "status": "built, component tests only",
      "refs": [
        "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:1-6",
        "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:283-289"
      ]
    },
    {
      "id": "job.files",
      "label": "Bridge files",
      "code": "C:/wh3-agent/bridge",
      "kind": "file",
      "where": "Windows game",
      "x": 470,
      "y": 34,
      "w": 210,
      "h": 60,
      "note":
        "menu.json, observation.json and orders.json: the only way the Python side and the game's scripts talk.",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/engine/mailbox.py:1-3"]
    },
    {
      "id": "job.frontend",
      "label": "Menu script",
      "code": "twwarhammer3_frontend.lua",
      "kind": "process",
      "where": "Windows game",
      "x": 730,
      "y": 34,
      "w": 210,
      "h": 60,
      "note":
        "Our Lua script in the main menu: it runs the steps in menu.json, one UI action at a time.",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/mod/script/frontend/mod/twwarhammer3_frontend.lua:1-9"]
    },
    {
      "id": "job.queue",
      "label": "The queue",
      "code": "scripts/wh3_queue.py",
      "kind": "process",
      "where": "WSL Python",
      "x": 20,
      "y": 146,
      "w": 180,
      "h": 52,
      "note": "Runs a frozen plan of play jobs, one at a time. This job was one entry of a plan.",
      "status": "built, component tests only",
      "refs": ["scripts/wh3_queue.py:1-3"]
    },
    {
      "id": "job.setup",
      "label": "Scenario setup",
      "code": "battle/setup.py",
      "kind": "process",
      "where": "WSL Python",
      "x": 20,
      "y": 222,
      "w": 180,
      "h": 52,
      "note":
        "Turns the scenario into the menu steps that build this custom battle, and checks the result.",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/battle/setup.py:1-3", "src/twwarhammer3/battle/play.py:114"]
    },
    {
      "id": "job.play",
      "label": "Play job",
      "code": "battle/play.py",
      "kind": "process",
      "where": "WSL Python",
      "x": 290,
      "y": 172,
      "w": 240,
      "h": 64,
      "note": "Owns the game for the whole job, plays each episode and records it.",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/battle/play.py:1", "src/twwarhammer3/battle/play.py:186-197"]
    },
    {
      "id": "job.policy",
      "label": "Model controller",
      "code": "battle/llm.py (llm_rules)",
      "kind": "agent",
      "where": "WSL Python",
      "x": 720,
      "y": 172,
      "w": 230,
      "h": 64,
      "note":
        "Writes the prompt from what our side can see, asks the model, and checks its orders.",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/battle/llm.py:1", "src/twwarhammer3/battle/play.py:530-536"]
    },
    {
      "id": "job.report",
      "label": "Report",
      "code": "twwarhammer3 report",
      "kind": "process",
      "where": "WSL Python",
      "x": 20,
      "y": 316,
      "w": 180,
      "h": 52,
      "note": "Run by hand, offline: reads finished jobs and writes tables and an HTML page.",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/battle/report.py:1"]
    },
    {
      "id": "job.evidence",
      "label": "Episode files",
      "code": "trace.jsonl · result.json",
      "kind": "file",
      "where": "WSL Python",
      "x": 290,
      "y": 316,
      "w": 200,
      "h": 52,
      "note":
        "Every state, model exchange, decision and acknowledgement, plus the result. Kept under runs/, not in Git.",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/battle/play.py:161"]
    },
    {
      "id": "job.results",
      "label": "Results register",
      "code": "docs/twwarhammer3/results.csv",
      "kind": "file",
      "where": "WSL Python",
      "x": 512,
      "y": 316,
      "w": 198,
      "h": 52,
      "note": "One row per episode, committed with the log.",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/battle/stats.py:1-3", "src/twwarhammer3/battle/play.py:161"]
    },
    {
      "id": "job.provider",
      "label": "OpenRouter",
      "code": "GLM 5.3, low effort",
      "kind": "outside service",
      "where": "cloud API",
      "x": 720,
      "y": 404,
      "w": 230,
      "h": 52,
      "note":
        "The model service this job named; each call is paid and recorded in the OpenRouter ledger.",
      "status": "outside our code: the provider APIs (src/gameai/providers.py:92)",
      "refs": ["src/gameai/providers.py:92"]
    }
  ],
  "wires": [
    {
      "id": "job.queue>play",
      "from": "job.queue",
      "to": "job.play",
      "label": "starts the job",
      "status": "built, component tests only",
      "refs": ["scripts/wh3_queue.py:1-3"]
    },
    {
      "id": "job.setup>play",
      "from": "job.setup",
      "to": "job.play",
      "label": "menu steps",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/battle/play.py:114"]
    },
    {
      "id": "job.play>game",
      "from": "job.play",
      "to": "job.game",
      "label": "launches",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/battle/play.py:197"]
    },
    {
      "id": "job.play>files",
      "from": "job.play",
      "to": "job.files",
      "label": "menu.json, orders.json",
      "bend": 46,
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/battle/play.py:243", "src/twwarhammer3/engine/mailbox.py:212"]
    },
    {
      "id": "job.files>play",
      "from": "job.files",
      "to": "job.play",
      "label": "state",
      "bend": 46,
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/engine/mailbox.py:287"]
    },
    {
      "id": "job.files>frontend",
      "from": "job.files",
      "to": "job.frontend",
      "label": "menu steps",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/mod/script/frontend/mod/twwarhammer3_frontend.lua:1-4"]
    },
    {
      "id": "job.files>battle",
      "from": "job.files",
      "to": "job.battle",
      "label": "orders",
      "bend": 18,
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:1375-1377"]
    },
    {
      "id": "job.battle>files",
      "from": "job.battle",
      "to": "job.files",
      "label": "state",
      "bend": 18,
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:759-762"]
    },
    {
      "id": "job.play>policy",
      "from": "job.play",
      "to": "job.policy",
      "label": "what our side sees",
      "bend": -24,
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/battle/play.py:530-536"]
    },
    {
      "id": "job.policy>play",
      "from": "job.policy",
      "to": "job.play",
      "label": "orders",
      "bend": -24,
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/battle/llm.py:1"]
    },
    {
      "id": "job.policy>provider",
      "from": "job.policy",
      "to": "job.provider",
      "label": "prompt",
      "bend": -30,
      "status": "built, component tests only",
      "refs": ["src/gameai/llm.py:1"]
    },
    {
      "id": "job.provider>policy",
      "from": "job.provider",
      "to": "job.policy",
      "label": "reply",
      "bend": -30,
      "status": "built, component tests only",
      "refs": ["src/gameai/llm.py:1"]
    },
    {
      "id": "job.play>evidence",
      "from": "job.play",
      "to": "job.evidence",
      "label": "trace rows",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/battle/play.py:1"]
    },
    {
      "id": "job.play>results",
      "from": "job.play",
      "to": "job.results",
      "label": "one row",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/battle/play.py:161"]
    },
    {
      "id": "job.evidence>report",
      "from": "job.evidence",
      "to": "job.report",
      "label": "read offline",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/battle/report.py:1"]
    }
  ],
  "flows": [
    {
      "id": "story",
      "title": "One play job",
      "story": true,
      "speed": 0.25,
      "steps": [
        {
          "caption":
            "The queue runs one play command: GLM 5.3 will command our side in one custom battle.",
          "dots": [["job.queue>play"]],
          "box": "job.play",
          "message": { "example": "job", "key": "command" },
          "refs": ["scripts/wh3_queue.py:1-3", "src/twwarhammer3/battle/play.py:105"]
        },
        {
          "caption":
            "The play job launches the game, and the menu script clicks through the custom battle screen.",
          "dots": [["job.play>game"], ["job.setup>play", "job.play>files", "job.files>frontend"]],
          "box": "job.frontend",
          "message": { "example": "job", "key": "setup" },
          "refs": [
            "src/twwarhammer3/battle/play.py:186-197",
            "src/twwarhammer3/battle/play.py:243",
            "src/twwarhammer3/mod/script/frontend/mod/twwarhammer3_frontend.lua:1-9"
          ]
        },
        {
          "caption":
            "The battle starts: our Swordsmen and Knights against three enemy Swordsmen, on a very hard setting.",
          "dots": [["job.battle>files", "job.files>play"]],
          "box": "job.battle",
          "message": { "example": "job", "key": "start" },
          "map": { "example": "job", "key": "r1" },
          "refs": ["src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:759-762"]
        },
        {
          "caption":
            "First decision: the model sees the state at 5.3 s and plans a frontal advance and a wide Knights flank.",
          "dots": [
            ["job.play>policy", "job.policy>provider", "job.provider>policy", "job.policy>play"]
          ],
          "box": "job.policy",
          "message": { "example": "job", "key": "r1" },
          "map": { "example": "job", "key": "r1" },
          "refs": ["src/twwarhammer3/battle/play.py:530-536", "src/twwarhammer3/battle/llm.py:1"]
        },
        {
          "caption":
            "The battle never waits for the model: orders based on the 79.7 s state apply at 83.0 s.",
          "dots": [["job.play>files", "job.files>battle"]],
          "box": "job.battle",
          "message": { "example": "job", "key": "r25" },
          "map": { "example": "job", "key": "r25" },
          "refs": [
            "src/twwarhammer3/engine/mailbox.py:212",
            "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:1375-1377"
          ]
        },
        {
          "caption":
            "By 329 s the Knights are routing; the model's last order sends the Swordsmen at the weakest enemy.",
          "dots": [
            ["job.play>policy", "job.policy>provider", "job.provider>policy", "job.policy>play"]
          ],
          "box": "job.policy",
          "message": { "example": "job", "key": "r88" },
          "map": { "example": "job", "key": "r88" },
          "refs": ["src/twwarhammer3/battle/llm.py:1"]
        },
        {
          "caption":
            "The engine reports a loss at 335 s; the play job records the episode and appends one results.csv row.",
          "dots": [
            ["job.battle>files", "job.files>play"],
            ["job.play>evidence"],
            ["job.play>results"]
          ],
          "box": "job.results",
          "message": { "example": "job", "key": "row" },
          "refs": ["src/twwarhammer3/battle/play.py:161", "src/twwarhammer3/battle/stats.py:1-3"]
        },
        {
          "caption":
            "Later, report reads the episode files offline; this report was built for this page, not the published one.",
          "dots": [["job.evidence>report"]],
          "box": "job.report",
          "message": { "example": "job", "key": "report" },
          "refs": [
            "src/twwarhammer3/battle/report.py:1",
            "configs/twwarhammer3/benchmark_jobs.json"
          ]
        }
      ]
    }
  ]
});
