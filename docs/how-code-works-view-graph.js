"use strict";
// The "How does a graph play a battle with no model in it?" story of docs/how-code-works.html.
// The 8 step boxes and their exits are generated from the battle's frozen graphs
// (docs/how-code-works-example-graph.js, scripts/diagram_examples.py graph); the bands, the Graph
// author and Battle script boxes, their wires and the steps are hand-written. Rules:
// docs/how-code-works-plan.md sections 2 and 5; design: runs/control-methods-20261101/
// final-spec.md. Strict JSON inside push( ... ); keep Prettier's --quote-props preserve
// --trailing-comma none. The view rests on JUDGEMENT? docs/how-code-works.html GaP drawn in the page;
// its steps rest on JUDGEMENT? scripts/diagram_examples.py Graph story moments.
// JUDGEMENT?: Graph battle layout — Claude Code, 2026-11-01: three side-by-side bands, Cloud API
// (Graph author) left, WSL Python (one row per member) middle, Windows game (Battle script)
// right; each exit to the next box arcs above its row. Alternative: the spec's stacked bands,
// which leave no clear path from a top band to the lower row; only looks rest on it.
DIAGRAM.tabs.push({
  "id": "graph",
  "title": "One graph battle",
  "question": "How does a graph play a battle with no model in it?",
  "takeaway":
    "Models write one graph per member before the battle; during it no model is asked, and the members take turns, each graph moving at most one step per view it gets.",
  "summary":
    "gap-initial-02, 1 Nov: graphs written by Haiku 5.5 before the battle; lost at 618.2 s by engine result; one battle, no strength claim.",
  "commit": "ad43a37",
  "reviewed": "2026-11-01",
  "example": "graph",
  "facts": {
    "graph_ops": [
      "charge",
      "contact",
      "end",
      "engage",
      "hold",
      "move",
      "owned",
      "select_target",
      "shoot"
    ]
  },
  "merge": true,
  "generated": {
    "example": "graph",
    "key": "graph"
  },
  "size": [1100, 372],
  "bands": [
    {
      "where": "Cloud API: before the battle",
      "x": 0,
      "y": 0,
      "w": 218,
      "h": 372
    },
    {
      "where": "WSL Python: during the battle, no model",
      "x": 226,
      "y": 0,
      "w": 742,
      "h": 372
    },
    {
      "where": "Windows game",
      "x": 976,
      "y": 0,
      "w": 124,
      "h": 372
    }
  ],
  "under": [
    "gap-initial-02, 1 Nov: graphs written by Haiku 5.5 before the battle; lost at 618.2 s by engine result; one battle, no strength claim.",
    "Hidden: the line's Observe melee contact step, which never ran, and 9 exits never taken in this battle (5 empty, 2 cancelled, that step's yes and no).",
    "graph-view draws the whole graph: twwarhammer3 graph-view runs/twwarhammer3/battle/gap-initial-02-20261101 --output runs/twwarhammer3/reports/NAME.html."
  ],
  "elements": [
    {
      "id": "g.author",
      "label": "Graph author",
      "code": "graph-author · Haiku 5.5",
      "kind": "agent",
      "where": "Cloud API",
      "x": 24,
      "y": 169,
      "w": 170,
      "h": 46,
      "note":
        "A coordinator splits the task, then one specialist per member writes that member's graph; this battle's graphs took 3 calls, about 20 s of wall clock and $0.0025.",
      "command":
        "uv run python -m twwarhammer3 graph-author --task TASK --budget-usd USD --output DIR; add --previous DIR --evidence EPISODE to revise after a battle",
      "status": {
        "text":
          "agreed offline check: WH3 initial GaP, whose canned author and revision cases passed at d6dfe92, and the initiation check at 4f0c3fc; neither establishes learning or live effects",
        "refs": ["docs/agreed-checks.md:72-82", "docs/agreed-checks.md:18-33"]
      },
      "refs": [
        "src/twwarhammer3/battle/graph_author.py:1",
        "src/twwarhammer3/__main__.py:186-203",
        "src/twwarhammer3/battle/graph_author.py:327-333",
        "src/twwarhammer3/battle/graph_author.py:344-360",
        "runs/twwarhammer3/gap-20261101/initial-02/manifest.json"
      ]
    },
    {
      "id": "g.battle",
      "label": "Battle script",
      "code": "tick() · poll()",
      "kind": "process",
      "where": "Windows game",
      "x": 984,
      "y": 170,
      "w": 108,
      "h": 44,
      "note": "Applies one request per tick and writes the state.",
      "status": "built, component tests only",
      "refs": [
        "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:1313-1317",
        "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua:1368"
      ]
    }
  ],
  "wires": [
    {
      "id": "g.author>cavalry.start",
      "from": "g.author",
      "to": "cavalry.start",
      "label": "writes the cavalry graph",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/battle/graph_author.py:344-360"]
    },
    {
      "id": "g.author>line.acquire",
      "from": "g.author",
      "to": "line.acquire",
      "label": "writes the line graph",
      "status": "built, component tests only",
      "refs": ["src/twwarhammer3/battle/graph_author.py:344-360"]
    },
    {
      "id": "cavalry.charge>g.battle",
      "from": "cavalry.charge",
      "to": "g.battle",
      "label": "charge orders",
      "status": "built, component tests only",
      "refs": [
        "src/twwarhammer3/battle/skill_contracts.py:131-140",
        "src/twwarhammer3/battle/team.py:335-344"
      ]
    },
    {
      "id": "line.attack>g.battle",
      "from": "line.attack",
      "to": "g.battle",
      "label": "attack orders",
      "status": "built, component tests only",
      "refs": [
        "src/twwarhammer3/battle/skill_contracts.py:131-140",
        "src/twwarhammer3/battle/team.py:335-344"
      ]
    }
  ],
  "flows": [
    {
      "id": "story",
      "title": "Story",
      "story": true,
      "speed": 0.25,
      "steps": [
        {
          "caption":
            "Before the battle, three Haiku calls, a coordinator and two specialists, write one graph per member.",
          "dots": [
            { "path": ["g.author>cavalry.start"], "who": "A" },
            { "path": ["g.author>line.acquire"], "who": "B" }
          ],
          "box": "g.author",
          "who": "model",
          "message": {
            "example": "graph",
            "key": "author"
          },
          "map": {
            "example": "graph",
            "key": "start"
          },
          "refs": [
            "src/twwarhammer3/battle/graph_author.py:327-333",
            "src/twwarhammer3/battle/graph_author.py:344-360"
          ]
        },
        {
          "caption":
            "From 5.3 s the line's graph takes one step per view it gets: units, nearest enemy Swordsmen 2 (e2), attack.",
          "dots": [["line.acquire>select", "line.select>refresh", "line.refresh>attack"]],
          "box": "line.attack",
          "who": "B",
          "message": {
            "example": "graph",
            "key": "line"
          },
          "map": {
            "example": "graph",
            "key": "start"
          },
          "refs": [
            "src/twwarhammer3/battle/graph.py:21-23",
            "src/twwarhammer3/battle/graph.py:206-225",
            "src/twwarhammer3/battle/team.py:312-344"
          ],
          "rests": [
            {
              "file": "src/twwarhammer3/battle/graph.py",
              "line": 21,
              "name": "G4 Graph limits"
            },
            {
              "file": "src/twwarhammer3/battle/graph.py",
              "line": 211,
              "name": "G4 Target choice"
            }
          ]
        },
        {
          "caption":
            "Engage sends “Swordsmen (f1) attack Swordsmen 2 (e2)”; the game applies it at 8.0 s, but the step keeps running.",
          "dots": [["line.attack>g.battle"]],
          "box": "g.battle",
          "who": "B",
          "message": {
            "example": "graph",
            "key": "accepted"
          },
          "map": {
            "example": "graph",
            "key": "attack"
          },
          "refs": [
            "src/twwarhammer3/battle/controllers.py:40-41",
            "src/twwarhammer3/battle/skill_contracts.py:119-124"
          ]
        },
        {
          "caption":
            "Meanwhile the cavalry's graph asks “is anyone in melee?” at every second view; it answers no 542 times.",
          "dots": [
            {
              "path": ["cavalry.start>start"]
            }
          ],
          "every": 500,
          "box": "cavalry.start",
          "who": "A",
          "message": {
            "example": "graph",
            "key": "contact"
          },
          "map": {
            "example": "graph",
            "key": "walk"
          },
          "refs": [
            "src/twwarhammer3/battle/graph.py:203-205",
            "src/twwarhammer3/battle/graph_author.py:33",
            "src/twwarhammer3/battle/team.py:312-344"
          ],
          "rests": [
            {
              "file": "src/twwarhammer3/battle/graph.py",
              "line": 21,
              "name": "G4 Graph limits"
            }
          ]
        },
        {
          "caption":
            "The walk is long: engage gives up after 60 s without melee and starts over, five times before contact.",
          "dots": [
            {
              "path": ["line.attack>acquire"],
              "fail": true
            }
          ],
          "box": "line.acquire",
          "who": "B",
          "message": {
            "example": "graph",
            "key": "deadlines"
          },
          "map": {
            "example": "graph",
            "key": "deadline"
          },
          "refs": [
            "src/twwarhammer3/battle/skill_contracts.py:17-22",
            "src/twwarhammer3/battle/skill_contracts.py:103-105"
          ],
          "rests": [
            {
              "file": "src/twwarhammer3/battle/skill_contracts.py",
              "line": 17,
              "name": "G4 Skill limits"
            }
          ]
        },
        {
          "caption":
            "At 334.7 s the Swordsmen reach Swordsmen 2 (e2); engage is done only once the game shows targeting and melee.",
          "dots": [["line.attack>acquire"]],
          "box": "line.attack",
          "who": "B",
          "message": {
            "example": "graph",
            "key": "melee"
          },
          "map": {
            "example": "graph",
            "key": "melee"
          },
          "refs": ["src/twwarhammer3/battle/skill_contracts.py:119-124"]
        },
        {
          "caption":
            "Contact answers yes; the cavalry picks Swordsmen 2 (e2), the enemy in melee, and orders the charge at 336.8 s.",
          "dots": [
            [
              "cavalry.start>own",
              "cavalry.own>sel",
              "cavalry.sel>charge",
              "cavalry.charge>g.battle"
            ]
          ],
          "box": "g.battle",
          "who": "A",
          "message": {
            "example": "graph",
            "key": "charge"
          },
          "map": {
            "example": "graph",
            "key": "charge"
          },
          "refs": [
            "src/twwarhammer3/battle/graph.py:206-225",
            "src/twwarhammer3/battle/graph_author.py:32",
            "src/twwarhammer3/battle/graph_author.py:37"
          ],
          "rests": [
            {
              "file": "src/twwarhammer3/battle/graph.py",
              "line": 211,
              "name": "G4 Target choice"
            }
          ]
        },
        {
          "caption":
            "At 386.3 s the charge counts as done: the Knights (f2), in melee, target Swordsmen 2 (e2) 129 m away.",
          "dots": [["cavalry.charge>own"]],
          "box": "cavalry.charge",
          "who": "A",
          "message": {
            "example": "graph",
            "key": "witness"
          },
          "map": {
            "example": "graph",
            "key": "witness"
          },
          "refs": ["src/twwarhammer3/battle/skill_contracts.py:119-124"]
        }
      ]
    },
    {
      "id": "replay",
      "title": "Whole battle",
      "replay": "replay",
      "speeds": [1, 4, 16],
      "speed": 4,
      "steps": []
    }
  ]
});
