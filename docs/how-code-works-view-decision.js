"use strict";
// The "What does the model see and send at one decision?" story of docs/how-code-works.html.
// Hand-written; rules: docs/how-code-works-plan.md sections 2 and 5. Strict JSON inside push( ... )
// (scripts/check.py and scripts/diagram_examples.py read it); keep Prettier's --quote-props
// preserve --trailing-comma none. Messages and maps: docs/how-code-works-example-decision.js.
DIAGRAM.tabs.push({
  "id": "decision",
  "title": "One decision",
  "question": "What does the model see and send at one decision?",
  "takeaway":
    "The model decides from a state that is already seconds old when its order applies, because the battle never waits for it.",
  "summary":
    "Request 25 of the 20 Oct battle: the state at 79.7 s, the reply, and the order applied at 83.0 s.",
  "commit": "7bf32e6",
  "reviewed": "2026-11-01",
  "example": "decision",
  "facts": {
    "hidden_keys": ["evaluation", "final", "setup", "native"]
  },
  "size": [1000, 470],
  "bands": [
    {
      "where": "Windows game",
      "x": 0,
      "y": 0,
      "w": 1000,
      "h": 120
    },
    {
      "where": "WSL Python",
      "x": 0,
      "y": 128,
      "w": 1000,
      "h": 258
    },
    {
      "where": "cloud API",
      "x": 0,
      "y": 394,
      "w": 1000,
      "h": 76
    }
  ],
  "elements": [
    {
      "id": "d.orders",
      "label": "Orders file",
      "code": "orders.json",
      "kind": "file",
      "where": "Windows game",
      "x": 40,
      "y": 34,
      "w": 200,
      "h": 60,
      "note": "The play loop writes one request here; the battle script reads and deletes it.",
      "status": "built, component tests only",
      "refs": [
        "src/twwarhammer3/engine/mailbox.py:212",
        "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:1375-1377"
      ]
    },
    {
      "id": "d.battle",
      "label": "Battle script",
      "code": "tick() · poll()",
      "kind": "process",
      "where": "Windows game",
      "x": 330,
      "y": 34,
      "w": 210,
      "h": 60,
      "note":
        "Polls orders.json on real time; on battle time, each tick applies the waiting request and writes the state.",
      "status": "built, component tests only",
      "refs": [
        "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:1313-1317",
        "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:1368",
        "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:1101-1103"
      ]
    },
    {
      "id": "d.obs",
      "label": "State file",
      "code": "observation.json",
      "kind": "file",
      "where": "Windows game",
      "x": 630,
      "y": 34,
      "w": 220,
      "h": 60,
      "note":
        "The newest state only: our units, enemy units while our side can see them, and hidden totals that the play loop strips before a policy sees them.",
      "status": "built, component tests only",
      "refs": [
        "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:759-762",
        "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:283-289",
        "src/twwarhammer3/engine/mailbox.py:91-92"
      ]
    },
    {
      "id": "d.play",
      "label": "Play loop",
      "code": "play.py _drive",
      "kind": "process",
      "where": "WSL Python",
      "x": 330,
      "y": 170,
      "w": 210,
      "h": 64,
      "note":
        "Reads the newest state, asks the policy only when no request is outstanding, and writes the request.",
      "status": "built, component tests only",
      "refs": [
        "src/twwarhammer3/battle/play.py:581",
        "src/twwarhammer3/battle/play.py:662-663",
        "src/twwarhammer3/battle/play.py:724"
      ]
    },
    {
      "id": "d.public",
      "label": "Public view",
      "code": "play.py public()",
      "kind": "process",
      "where": "WSL Python",
      "x": 640,
      "y": 170,
      "w": 210,
      "h": 64,
      "note":
        "Today's code removes the hidden keys (evaluation, final, setup, native) before a policy sees the state; on 20 Oct an inline filter removed the first three.",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/battle/play.py:530-536", "src/twwarhammer3/protocol.py:45"]
    },
    {
      "id": "d.policy",
      "label": "Model controller",
      "code": "battle/llm.py (llm_rules)",
      "kind": "agent",
      "where": "WSL Python",
      "x": 630,
      "y": 290,
      "w": 220,
      "h": 64,
      "note":
        "Builds the prompt (notes, recent decisions, timing, the state) and checks the reply's orders.",
      "status": "built, component tests only",
      "refs": [
        "src/twwarhammer3/battle/llm.py:1",
        "src/twwarhammer3/battle/llm.py:382",
        "src/twwarhammer3/battle/llm.py:454-461",
        "src/twwarhammer3/battle/llm.py:615"
      ]
    },
    {
      "id": "d.model",
      "label": "Model call",
      "code": "gameai/llm.py Model.ask",
      "kind": "process",
      "where": "WSL Python",
      "x": 330,
      "y": 290,
      "w": 220,
      "h": 64,
      "note":
        "Checks the call's worst-case cost against the budget, then sends it; since 21 Oct (commit e554dd5) it also holds that cost in the ledger until the call returns.",
      "status": "built, component tests only",
      "refs": ["src/gameai/llm.py:352", "src/gameai/llm.py:376-378", "src/gameai/llm.py:469"]
    },
    {
      "id": "d.provider",
      "label": "OpenRouter",
      "code": "GLM 5.3, low effort",
      "kind": "outside service",
      "where": "cloud API",
      "x": 330,
      "y": 404,
      "w": 220,
      "h": 52,
      "note": "The model service this job named.",
      "status": "outside our code: the provider APIs (src/gameai/providers.py:92)",
      "refs": ["src/gameai/providers.py:92"]
    }
  ],
  "wires": [
    {
      "id": "d.battle>obs",
      "from": "d.battle",
      "to": "d.obs",
      "label": "writes the state",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:759-762"]
    },
    {
      "id": "d.obs>play",
      "from": "d.obs",
      "to": "d.play",
      "label": "read every 0.1 s",
      "status": "built, component tests only",
      "refs": [
        "src/twwarhammer3/engine/mailbox.py:173",
        "src/twwarhammer3/engine/mailbox.py:287-300"
      ]
    },
    {
      "id": "d.play>public",
      "from": "d.play",
      "to": "d.public",
      "label": "the newest state",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/battle/play.py:662"]
    },
    {
      "id": "d.public>policy",
      "from": "d.public",
      "to": "d.policy",
      "label": "what our side sees",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/battle/play.py:530-536"]
    },
    {
      "id": "d.policy>model",
      "from": "d.policy",
      "to": "d.model",
      "label": "prompt",
      "status": "built, component tests only",
      "refs": ["src/gameai/llm.py:469"],
      "bend": -24
    },
    {
      "id": "d.model>policy",
      "from": "d.model",
      "to": "d.policy",
      "label": "reply",
      "status": "built, component tests only",
      "refs": ["src/gameai/llm.py:469"],
      "bend": -24
    },
    {
      "id": "d.model>provider",
      "from": "d.model",
      "to": "d.provider",
      "label": "request",
      "status": "built, component tests only",
      "refs": ["src/gameai/llm.py:376-378"],
      "bend": -26
    },
    {
      "id": "d.provider>model",
      "from": "d.provider",
      "to": "d.model",
      "label": "reply",
      "status": "built, component tests only",
      "refs": ["src/gameai/llm.py:469"],
      "bend": -26
    },
    {
      "id": "d.policy>play",
      "from": "d.policy",
      "to": "d.play",
      "label": "orders",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/battle/llm.py:615"]
    },
    {
      "id": "d.play>orders",
      "from": "d.play",
      "to": "d.orders",
      "label": "request 25",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/battle/play.py:724", "src/twwarhammer3/engine/mailbox.py:212"]
    },
    {
      "id": "d.orders>battle",
      "from": "d.orders",
      "to": "d.battle",
      "label": "applied at a tick",
      "status": "built, component tests only",
      "refs": [
        "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:1375-1377",
        "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:1313-1317"
      ]
    }
  ],
  "flows": [
    {
      "id": "story",
      "title": "One decision",
      "story": true,
      "speed": 0.25,
      "steps": [
        {
          "caption":
            "At 79.7 s the battle script writes the state, hidden totals included; the play loop reads it within 0.1 s.",
          "dots": [["d.battle>obs", "d.obs>play"]],
          "box": "d.play",
          "message": {
            "example": "decision",
            "key": "saw"
          },
          "map": {
            "example": "decision",
            "key": "saw"
          },
          "refs": [
            "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:759-762",
            "src/twwarhammer3/engine/mailbox.py:287-300"
          ]
        },
        {
          "caption":
            "The public view drops the hidden keys, and the model controller turns the rest into a prompt.",
          "dots": [["d.play>public", "d.public>policy"]],
          "box": "d.policy",
          "message": {
            "example": "decision",
            "key": "prompt"
          },
          "refs": ["src/twwarhammer3/battle/play.py:530-536", "src/twwarhammer3/battle/llm.py:382"]
        },
        {
          "caption":
            "The prompt goes to GLM 5.3 through OpenRouter, and the model takes 2.8 s to reply.",
          "dots": [["d.policy>model", "d.model>provider"]],
          "box": "d.provider",
          "message": {
            "example": "decision",
            "key": "call"
          },
          "refs": ["src/gameai/llm.py:352", "src/gameai/llm.py:469"]
        },
        {
          "caption":
            "The battle never waits: meanwhile the game keeps writing newer states, which this decision never sees.",
          "dots": [["d.battle>obs"]],
          "box": "d.battle",
          "message": {
            "example": "decision",
            "key": "trace"
          },
          "refs": [
            "src/twwarhammer3/battle/play.py:662-663",
            "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:759-762"
          ]
        },
        {
          "caption":
            "The reply holds one order and a reason: run the Knights (f2) west, out of the melee.",
          "dots": [["d.provider>model", "d.model>policy"]],
          "box": "d.policy",
          "message": {
            "example": "decision",
            "key": "reply"
          },
          "refs": ["src/gameai/llm.py:469", "src/twwarhammer3/battle/llm.py:615"]
        },
        {
          "caption":
            "The play loop writes request 25, based on the 79.7 s state, to orders.json, then logs it.",
          "dots": [["d.policy>play", "d.play>orders"]],
          "box": "d.orders",
          "message": {
            "example": "decision",
            "key": "request"
          },
          "refs": [
            "src/twwarhammer3/battle/play.py:724-728",
            "src/twwarhammer3/engine/mailbox.py:212"
          ]
        },
        {
          "caption":
            "The battle script applies request 25 at 83.0 s, 3.3 s after the state the model saw.",
          "dots": [["d.orders>battle"]],
          "box": "d.battle",
          "message": {
            "example": "decision",
            "key": "ack"
          },
          "map": {
            "example": "decision",
            "key": "after"
          },
          "refs": [
            "src/twwarhammer3/engine/mailbox.py:212",
            "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:1101-1103",
            "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:1313-1317"
          ]
        },
        {
          "caption":
            "The next prompt tells the model its last order arrived 3.3 s late, and to expect a similar delay.",
          "dots": [["d.obs>play", "d.play>public", "d.public>policy"]],
          "box": "d.policy",
          "message": {
            "example": "decision",
            "key": "next"
          },
          "refs": [
            "src/twwarhammer3/battle/llm.py:454-461",
            "src/twwarhammer3/battle/play.py:499-507"
          ]
        }
      ]
    }
  ]
});
