"use strict";
// The "How do two members share one army?" story of docs/how-code-works.html. Hand-written; rules:
// docs/how-code-works-plan.md sections 2 and 5. The lanes are copied from the frozen Team tab's
// probe flow (claims checked at 21f6204). Strict JSON inside push( ... ); keep Prettier's
// --quote-props preserve --trailing-comma none. Messages and maps: how-code-works-example-members.js.
DIAGRAM.tabs.push({
  "id": "members",
  "title": "Two members, one army",
  "question": "How do two members share one army?",
  "takeaway":
    "Each member thinks about its own units on its own clock, and each request carries at most one member's batch, so neither waits for the other.",
  "summary":
    "Probe 1 of the scripted team's live check on 31 Oct: the infantry member waits 3 s on purpose.",
  "commit": "7bf32e6",
  "reviewed": "2026-11-01",
  "example": "members",
  "size": [1000, 300],
  "bands": [
    {
      "where": "Windows game",
      "x": 0,
      "y": 0,
      "w": 1000,
      "h": 92
    },
    {
      "where": "WSL Python",
      "x": 0,
      "y": 100,
      "w": 1000,
      "h": 200
    }
  ],
  "elements": [
    {
      "id": "m.game",
      "label": "Battle script",
      "code": "tick() · poll()",
      "kind": "process",
      "where": "Windows game",
      "x": 300,
      "y": 22,
      "w": 180,
      "h": 54,
      "note": "Applies one request per tick and writes the state.",
      "status": "built, component tests only",
      "refs": [
        "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:1313-1317",
        "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:1368"
      ]
    },
    {
      "id": "m.obs",
      "label": "State file",
      "code": "observation.json",
      "kind": "file",
      "where": "Windows game",
      "x": 570,
      "y": 22,
      "w": 190,
      "h": 54,
      "note": "The newest state only.",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:759-762"]
    },
    {
      "id": "m.orders",
      "label": "Orders file",
      "code": "orders.json",
      "kind": "file",
      "where": "Windows game",
      "x": 20,
      "y": 22,
      "w": 190,
      "h": 54,
      "note": "The play loop is its only writer.",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/engine/mailbox.py:212"]
    },
    {
      "id": "m.play",
      "label": "Play loop",
      "code": "play.py _drive",
      "kind": "process",
      "where": "WSL Python",
      "x": 300,
      "y": 136,
      "w": 200,
      "h": 56,
      "note": "The only mailbox writer: one request at a time, whoever's batch it carries.",
      "status":
        "agreed live check: WH3 scripted two-member team (docs/agreed-checks.md:48); its live part passed 4/4 at 96bb137 and 3/4 at 1cc4582 (log.md)",
      "refs": [
        "src/twwarhammer3/battle/play.py:662-663",
        "src/twwarhammer3/battle/play.py:724",
        "src/twwarhammer3/battle/team.py:9-11",
        "docs/twwarhammer3/log.md:577-579"
      ]
    },
    {
      "id": "m.team",
      "label": "Team dispatcher",
      "code": "team.py TeamPolicy",
      "kind": "process",
      "where": "WSL Python",
      "x": 560,
      "y": 136,
      "w": 200,
      "h": 56,
      "note":
        "Splits the units by type, runs one call per member on two threads, and sends the oldest finished batch; no member waits for the other.",
      "status":
        "agreed live check: WH3 scripted two-member team (docs/agreed-checks.md:48); its live part passed 4/4 at 96bb137 and 3/4 at 1cc4582 (log.md)",
      "refs": [
        "src/twwarhammer3/battle/team.py:126-127",
        "src/twwarhammer3/battle/team.py:142",
        "src/twwarhammer3/battle/team.py:205-230",
        "src/twwarhammer3/battle/team.py:312-344",
        "docs/twwarhammer3/log.md:577-579"
      ]
    },
    {
      "id": "m.A",
      "label": "Cavalry member",
      "code": "owns the Knights (f2)",
      "kind": "agent",
      "where": "WSL Python",
      "x": 835,
      "y": 116,
      "w": 155,
      "h": 52,
      "note": "In the probe: one 20 m move, at once.",
      "status":
        "agreed live check: WH3 scripted two-member team (docs/agreed-checks.md:48); its live part passed 4/4 at 96bb137 and 3/4 at 1cc4582 (log.md)",
      "refs": [
        "docs/twwarhammer3/log.md:577-579",
        "src/twwarhammer3/battle/team.py:462-478",
        "src/twwarhammer3/battle/team.py:487-493"
      ]
    },
    {
      "id": "m.B",
      "label": "Infantry member",
      "code": "owns the Swordsmen (f1)",
      "kind": "agent",
      "where": "WSL Python",
      "x": 835,
      "y": 226,
      "w": 155,
      "h": 52,
      "note": "In the probe: waits 3 s, then one move.",
      "status":
        "agreed live check: WH3 scripted two-member team (docs/agreed-checks.md:48); its live part passed 4/4 at 96bb137 and 3/4 at 1cc4582 (log.md)",
      "refs": [
        "docs/twwarhammer3/log.md:577-579",
        "src/twwarhammer3/battle/team.py:462-478",
        "src/twwarhammer3/battle/team.py:487-493"
      ]
    }
  ],
  "wires": [
    {
      "id": "m.game>obs",
      "from": "m.game",
      "to": "m.obs",
      "label": "writes the state",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:759-762"]
    },
    {
      "id": "m.obs>play",
      "from": "m.obs",
      "to": "m.play",
      "label": "read every 0.1 s",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/engine/mailbox.py:287-300"]
    },
    {
      "id": "m.play>team",
      "from": "m.play",
      "to": "m.team",
      "label": "decide",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/battle/play.py:680", "src/twwarhammer3/battle/team.py:312"],
      "bend": -16
    },
    {
      "id": "m.team>play",
      "from": "m.team",
      "to": "m.play",
      "label": "one batch",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/battle/team.py:337-344"],
      "bend": -16
    },
    {
      "id": "m.team>A",
      "from": "m.team",
      "to": "m.A",
      "label": "its own view",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/battle/team.py:325-333"],
      "bend": -14
    },
    {
      "id": "m.A>team",
      "from": "m.A",
      "to": "m.team",
      "label": "batch",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/battle/team.py:242-248"],
      "bend": -14
    },
    {
      "id": "m.team>B",
      "from": "m.team",
      "to": "m.B",
      "label": "its own view",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/battle/team.py:325-333"],
      "bend": -14
    },
    {
      "id": "m.B>team",
      "from": "m.B",
      "to": "m.team",
      "label": "batch",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/battle/team.py:242-248"],
      "bend": -14
    },
    {
      "id": "m.play>orders",
      "from": "m.play",
      "to": "m.orders",
      "label": "one request",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/battle/play.py:724"]
    },
    {
      "id": "m.orders>game",
      "from": "m.orders",
      "to": "m.game",
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
      "title": "Two members, one army",
      "story": true,
      "timed": true,
      "clock":
        "battle time; steps inside one 300 ms round are spaced for legibility, and the members' calls are WSL times fitted to battle time",
      "start": 5300,
      "end": 10400,
      "speed": 0.25,
      "lanes": {
        "rows": [
          {
            "id": "game",
            "label": "game: applied"
          },
          {
            "id": "play",
            "label": "play loop: requests"
          },
          {
            "id": "A",
            "label": "member cavalry"
          },
          {
            "id": "B",
            "label": "member infantry"
          }
        ],
        "items": [
          {
            "row": "play",
            "label": "request 1",
            "from": 5300,
            "to": 5600
          },
          {
            "row": "play",
            "label": "request 2",
            "who": "A",
            "from": 5600,
            "to": 5900
          },
          {
            "row": "play",
            "label": "request 3",
            "from": 5900,
            "to": 6200
          },
          {
            "row": "play",
            "label": "request 4",
            "who": "A",
            "from": 6200,
            "to": 6500
          },
          {
            "row": "play",
            "label": "request 5",
            "from": 6500,
            "to": 6800
          },
          {
            "row": "play",
            "label": "request 6",
            "who": "A",
            "from": 6800,
            "to": 7100
          },
          {
            "row": "play",
            "label": "request 7",
            "from": 7100,
            "to": 7400
          },
          {
            "row": "play",
            "label": "request 8",
            "who": "A",
            "from": 7400,
            "to": 7700
          },
          {
            "row": "play",
            "label": "request 9",
            "from": 7700,
            "to": 8000
          },
          {
            "row": "play",
            "label": "request 10",
            "who": "A",
            "from": 8000,
            "to": 8300
          },
          {
            "row": "play",
            "label": "request 11",
            "from": 8300,
            "to": 8600
          },
          {
            "row": "play",
            "label": "request 12",
            "who": "A",
            "from": 8600,
            "to": 8900
          },
          {
            "row": "play",
            "label": "request 13",
            "who": "B",
            "from": 8900,
            "to": 9200
          },
          {
            "row": "play",
            "label": "request 14",
            "who": "A",
            "from": 9200,
            "to": 9500
          },
          {
            "row": "play",
            "label": "request 15",
            "who": "B",
            "from": 9500,
            "to": 9800
          },
          {
            "row": "play",
            "label": "request 16",
            "who": "A",
            "from": 9800,
            "to": 10100
          },
          {
            "row": "play",
            "label": "request 17",
            "who": "B",
            "from": 10100,
            "to": 10400
          },
          {
            "row": "A",
            "label": "cavalry-1",
            "input": 5300,
            "completed": 5300,
            "sent": 5600,
            "applied": 5900
          },
          {
            "row": "A",
            "label": "cavalry-2",
            "input": 5900,
            "completed": 5900,
            "sent": 6200,
            "applied": 6500
          },
          {
            "row": "A",
            "label": "cavalry-3",
            "input": 6500,
            "completed": 6500,
            "sent": 6800,
            "applied": 7100
          },
          {
            "row": "A",
            "label": "cavalry-4",
            "input": 7100,
            "completed": 7100,
            "sent": 7400,
            "applied": 7700
          },
          {
            "row": "A",
            "label": "cavalry-5",
            "input": 7700,
            "completed": 7700,
            "sent": 8000,
            "applied": 8300
          },
          {
            "row": "A",
            "label": "cavalry-6",
            "input": 8300,
            "completed": 8300,
            "sent": 8600,
            "applied": 8900
          },
          {
            "row": "A",
            "label": "cavalry-7",
            "input": 8900,
            "completed": 8900,
            "sent": 9200,
            "applied": 9500
          },
          {
            "row": "A",
            "label": "cavalry-8",
            "input": 9500,
            "completed": 9500,
            "sent": 9800,
            "applied": 10100
          },
          {
            "row": "A",
            "label": "cavalry-9",
            "input": 10100,
            "completed": 10100,
            "sent": 10400,
            "applied": 10700
          },
          {
            "row": "B",
            "label": "infantry-1",
            "input": 5300,
            "completed": 8590,
            "sent": 8900,
            "applied": 9200
          },
          {
            "row": "B",
            "label": "infantry-2",
            "input": 9200,
            "completed": 9200,
            "sent": 9500,
            "applied": 9800
          },
          {
            "row": "B",
            "label": "infantry-3",
            "input": 9800,
            "completed": 9800,
            "sent": 10100,
            "applied": 10400
          }
        ],
        "marks": [
          {
            "row": "game",
            "kind": "applied",
            "at": [
              5600, 5900, 6200, 6500, 6800, 7100, 7400, 7700, 8000, 8300, 8600, 8900, 9200, 9500,
              9800, 10100, 10400
            ]
          }
        ]
      },
      "steps": [
        {
          "at": 5300,
          "until": 5430,
          "caption":
            "At 5.3 s the team splits our army: cavalry gets the Knights (f2), infantry the Swordsmen (f1).",
          "dots": [["m.obs>play", "m.play>team"]],
          "box": "m.team",
          "message": {
            "example": "members",
            "key": "split"
          },
          "map": {
            "example": "members",
            "key": "start"
          },
          "refs": ["src/twwarhammer3/battle/team.py:205-230"]
        },
        {
          "at": 5430,
          "until": 5600,
          "caption":
            "Each member thinks on its own copy of the state; infantry waits 3 s on purpose, cavalry answers at once.",
          "dots": [["m.team>B"]],
          "box": "m.B",
          "who": "B",
          "refs": [
            "src/twwarhammer3/battle/team.py:325-333",
            "src/twwarhammer3/battle/team.py:462-478",
            "src/twwarhammer3/battle/team.py:487-493"
          ]
        },
        {
          "at": 5600,
          "until": 5900,
          "caption":
            "The play loop never waits for both: cavalry's move goes out alone as request 2, applied at 5.9 s.",
          "dots": [["m.A>team", "m.team>play", "m.play>orders", "m.orders>game"]],
          "box": "m.A",
          "who": "A",
          "message": {
            "example": "members",
            "key": "r2"
          },
          "map": {
            "example": "members",
            "key": "cavalry"
          },
          "refs": ["src/twwarhammer3/battle/team.py:337-344", "src/twwarhammer3/battle/play.py:724"]
        },
        {
          "at": 5900,
          "until": 6500,
          "caption":
            "The acknowledgement goes only to cavalry, whose batch it was; cavalry then starts its next call.",
          "dots": [["m.game>obs", "m.obs>play", "m.play>team", "m.team>A"]],
          "box": "m.A",
          "who": "A",
          "refs": [
            "src/twwarhammer3/battle/team.py:346-350",
            "src/twwarhammer3/battle/play.py:499-507"
          ]
        },
        {
          "at": 6500,
          "until": 8600,
          "caption":
            "Meanwhile a request goes every 0.3 s: idle polls and cavalry's empty batches, never a wait.",
          "dots": [["m.play>orders", "m.orders>game"]],
          "box": "m.play",
          "message": {
            "example": "members",
            "key": "idle"
          },
          "refs": [
            "src/twwarhammer3/battle/team.py:337-339",
            "src/twwarhammer3/battle/team.py:346-348"
          ],
          "every": 300
        },
        {
          "at": 8600,
          "until": 8900,
          "caption":
            "Infantry's move finishes at about 8.6 s and waits one round, behind cavalry's empty batch.",
          "dots": [["m.B>team"]],
          "box": "m.B",
          "who": "B",
          "refs": ["src/twwarhammer3/battle/team.py:339-341"]
        },
        {
          "at": 8900,
          "until": 9500,
          "caption":
            "Infantry's move goes as request 13, applied at 9.2 s: 3.9 s after the state infantry decided on.",
          "dots": [["m.team>play", "m.play>orders", "m.orders>game"]],
          "box": "m.B",
          "who": "B",
          "message": {
            "example": "members",
            "key": "r13"
          },
          "map": {
            "example": "members",
            "key": "infantry"
          },
          "refs": [
            "src/twwarhammer3/battle/team.py:277-278",
            "src/twwarhammer3/battle/team.py:292-298"
          ]
        },
        {
          "at": 9500,
          "until": 10400,
          "caption":
            "From then on the members take turns: each request carries one member's batch, so neither waits for the other.",
          "dots": [["m.team>play"]],
          "box": "m.team",
          "message": {
            "example": "members",
            "key": "alternate"
          },
          "refs": ["src/twwarhammer3/battle/team.py:340-341"]
        }
      ]
    }
  ]
});
