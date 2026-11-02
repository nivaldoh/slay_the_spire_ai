"use strict";
// The "When does each control method ask a model?" comparison of docs/how-code-works.html.
// Hand-written: question, takeaway, captions, step rows, card fields (1)-(4) and statuses. The
// lanes, side cells and card numbers come from docs/how-code-works-example-methods.js
// (scripts/diagram_examples.py methods). Rules: docs/how-code-works-plan.md sections 2 and 5;
// design: runs/control-methods-20261101/final-spec.md. Strict JSON inside push( ... ); keep
// Prettier's --quote-props preserve --trailing-comma none. Its numbers
// rest on JUDGEMENT? scripts/diagram_examples.py Example battles, Methods window, Resent rule.
// JUDGEMENT?: Basic is llm_rules — Claude Code, 2026-11-01, control-methods spec: the llm_rules
// arm its battle ran. Alternative: llm, the documented baseline (same code, other prompt); all
// basic numbers rest on it. Rests on JUDGEMENT docs/twwarhammer3/controllers.md Scored model arm.
// JUDGEMENT?: One view on two battles — Claude Code, 2026-11-01, control-methods spec: one battle
// per group, though plan section 2 says a story rests on one battle. Alternative: one lanes view
// per method, losing the side-by-side read; the comparison rests on it.
// JUDGEMENT?: Side cells not to scale — Claude Code, 2026-11-01, control-methods spec: one block
// per model call, wall-clock seconds as text. Alternative: proportional bars, putting WSL seconds
// beside battle seconds; how authoring time reads rests on it.
// JUDGEMENT?: Minimal set — Claude Code, 2026-11-01, control-methods spec: two new views; no cards
// table, authoring story or cadence tab. Alternative: a "Writing a graph" story; what the owner
// sees of authoring rests on it (side cells, steps 4 and 7, step 1 of One graph battle).
// JUDGEMENT?: Card fields — Claude Code, 2026-11-01, control-methods spec: 8 fields and a closed
// "where the model sits" list. Alternative: an 11-row card adding what a method reads and
// carries; how methods are compared rests on it.
// JUDGEMENT?: Comparison scaling — Claude Code, 2026-11-01, control-methods spec: one flow, up to
// 3 groups a flow, then "Basic vs X" flows. Alternative: every method on one clock. Basic as the
// reference rests on JUDGEMENT? docs/twwarhammer3/controllers.md Baseline and floor.
DIAGRAM.tabs.push({
  "id": "methods",
  "title": "Control methods",
  "question": "When does each control method ask a model?",
  "takeaway":
    "Basic asks a model at every decision while the battle runs; in this GaP battle models are asked only before and between battles and code plays the graphs (GaP's optional target hints, unused here, ask during a battle).",
  "summary":
    "Two recorded battles on the same scenario, 20 Oct (basic) and 1 Nov (GaP), over the first 30 s after deployment; one battle each.",
  "commit": "ad43a37",
  "reviewed": "2026-11-01",
  "example": ["methods-basic", "methods-gap"],
  "facts": {
    "model_policies": ["commander", "llm", "llm_rules", "team_llm_rules"],
    "scripted_policies": ["attack_nearest", "hold", "rush_nearest"],
    "versions": {
      "llm": "v22",
      "llm_rules": "v22",
      "commander": "v8",
      "skills": "v1.2",
      "team_llm_rules": "v22+t2"
    }
  },
  "size": [1000, 0],
  "bands": [],
  "elements": [],
  "wires": [],
  "banner": "Both run in one play loop: one request at a time, and the battle never waits.",
  "under": [
    "One battle each, same armies and map, different code versions: not a strength or speed contest.",
    "Not drawn yet: commander, team_llm_rules, skills, hold, attack_nearest, rush_nearest."
  ],
  "cards": {
    "basic": {
      "where": "In the loop: each decision waits for a model reply, and the battle does not wait.",
      "who": "The model, in each reply.",
      "writes": "Raw orders for our units, a reason and notes, as strict JSON.",
      "done": "Not judged by code; the next prompt says which orders the game accepted or refused.",
      "note": "Basic here is llm_rules; llm is the same code with another system prompt.",
      "stories": ["decision", "job"],
      "status": {
        "text":
          "built, component tests only: the WH3 UI request and session checks passed at 6291377; no agreed check of the decision cycle; strength unverified",
        "refs": ["docs/agreed-checks.md:116-119"]
      },
      "rests": [
        {
          "file": "docs/twwarhammer3/controllers.md",
          "line": 53,
          "name": "Scored model arm"
        },
        {
          "file": "src/twwarhammer3/battle/play.py",
          "line": 501,
          "name": "Delay"
        }
      ],
      "refs": [
        "src/twwarhammer3/battle/controllers.py:35-50",
        "src/twwarhammer3/battle/llm.py:59-82",
        "src/twwarhammer3/battle/llm.py:464-478",
        "src/twwarhammer3/battle/play.py:1-17",
        "src/twwarhammer3/battle/controllers.py:40",
        "src/twwarhammer3/battle/controllers.py:31-32",
        "docs/twwarhammer3/controllers.md:69-70"
      ]
    },
    "gap": {
      "where": [
        "Before the battle: a coordinator and one specialist per member write the graphs.",
        "Between battles: each specialist revises its graph from its member's public record; the coordinator sees no battle record."
      ],
      "who":
        "Python: each member's frozen graph; its skill steps (engage, charge) make the orders.",
      "writes": "One graph per member: its steps, and which step follows each outcome.",
      "done":
        "Only when the game shows the effect, like melee with the target; never on acceptance; fails after 60 s.",
      "note":
        "Optional beside the loop: target hints (graph_llm), at most every 30 battle seconds; not used in this battle.",
      "stories": ["graph", "members"],
      "status": {
        "text":
          "agreed live check: no-model live effects 3/3 at d12be58; target hints at 87518f9, one probe; agreed offline checks: the graph-view check at b8f8cb7, the initiation check at 4f0c3fc. 5 GaP battles on this scenario, all lost; two sent no orders before the 1205 s limit, because their written graphs waited for contact. Strength unverified. The melee check reads a unit's target and melee flag, not whom it fights",
        "refs": [
          "docs/agreed-checks.md:72-92",
          "docs/agreed-checks.md:34-58",
          "docs/agreed-checks.md:59-71",
          "docs/agreed-checks.md:18-33",
          "docs/twwarhammer3/results.csv:645-649",
          "docs/twwarhammer3/log.md:110-123",
          "src/twwarhammer3/battle/skill_contracts.py:119-122"
        ]
      },
      "rests": [
        {
          "file": "src/twwarhammer3/battle/skill_contracts.py",
          "line": 17,
          "name": "G4 Skill limits"
        },
        {
          "file": "src/twwarhammer3/battle/graph.py",
          "line": 21,
          "name": "G4 Graph limits"
        },
        {
          "file": "src/twwarhammer3/battle/play.py",
          "line": 501,
          "name": "Delay"
        }
      ],
      "refs": [
        "src/twwarhammer3/battle/controllers.py:35-50",
        "src/twwarhammer3/battle/graph.py:21-23",
        "src/twwarhammer3/battle/graph_author.py:327-333",
        "src/twwarhammer3/battle/graph_author.py:344-360",
        "src/twwarhammer3/battle/graph_author.py:175-179",
        "src/twwarhammer3/battle/skill_contracts.py:17-22",
        "src/twwarhammer3/battle/skill_contracts.py:100-124",
        "src/twwarhammer3/battle/graph_goals.py:24-31"
      ]
    }
  },
  "flows": [
    {
      "id": "compare",
      "title": "Basic vs GaP",
      "story": true,
      "static": true,
      "start": 5300,
      "end": 35300,
      "clock": "battle time, 5.3-35.3 s in the middle column; the side columns are not to scale",
      "speed": 0.25,
      "lanes": {
        "example": "methods",
        "key": "lanes",
        "legend":
          "pink bar: one wait for a model, from the view it read to its orders applying · tick: a graph step · bar: a skill step running · ◆ new orders · ▫ same orders sent again · no mark: current orders kept"
      },
      "steps": [
        {
          "rows": ["basic.model"],
          "caption":
            "Basic: the model is asked at every decision; each pink bar is one wait for its reply.",
          "message": {
            "example": "methods-basic",
            "key": "r1"
          },
          "refs": [
            "src/twwarhammer3/battle/llm.py:59-82",
            "src/twwarhammer3/battle/play.py:499-507"
          ],
          "rests": [
            {
              "file": "src/twwarhammer3/battle/play.py",
              "line": 501,
              "name": "Delay"
            }
          ]
        },
        {
          "rows": ["basic.model", "basic.orders"],
          "span": [5300, 8900],
          "caption":
            "Its first orders apply at 8.9 s from the view of 5.3 s; the battle never waited.",
          "message": {
            "example": "methods-basic",
            "key": "r1-applied"
          },
          "map": {
            "example": "methods-basic",
            "key": "r1"
          },
          "refs": [
            "src/twwarhammer3/battle/play.py:1-17",
            "src/twwarhammer3/battle/play.py:499-507"
          ],
          "rests": [
            {
              "file": "src/twwarhammer3/battle/play.py",
              "line": 501,
              "name": "Delay"
            }
          ]
        },
        {
          "rows": ["basic.orders"],
          "caption": "Of the 9 replies here, 2 send new orders; the other 7 keep the current ones.",
          "message": {
            "example": "methods-basic",
            "key": "r2"
          },
          "refs": ["src/twwarhammer3/battle/llm.py:464-469"]
        },
        {
          "rows": ["gap.model"],
          "caption":
            "GaP, left column: before the battle, three model calls write one graph per member, in about 20 s.",
          "message": {
            "example": "methods-gap",
            "key": "task"
          },
          "refs": [
            "src/twwarhammer3/battle/graph_author.py:327-333",
            "src/twwarhammer3/battle/graph_author.py:344-360",
            "runs/twwarhammer3/gap-20261101/initial-02/manifest.json"
          ]
        },
        {
          "rows": ["gap.model", "gap.cavalry", "gap.line"],
          "caption":
            "During the battle no model is asked: Python moves each member's graph at most one step per view it gets.",
          "message": {
            "example": "methods-gap",
            "key": "steps"
          },
          "refs": [
            "src/twwarhammer3/battle/graph.py:21-23",
            "src/twwarhammer3/battle/graph.py:172-174",
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
          "rows": ["gap.orders"],
          "span": [7400, 8000],
          "caption":
            "The line's attack on Swordsmen 2 (e2) applies at 8.0 s from the 7.4 s view; resent every 2.1-2.4 s.",
          "message": {
            "example": "methods-gap",
            "key": "order"
          },
          "map": {
            "example": "methods-gap",
            "key": "attack"
          },
          "refs": [
            "src/twwarhammer3/battle/skill_contracts.py:17-22",
            "src/twwarhammer3/battle/skill_contracts.py:136-140"
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
          "rows": ["gap.model"],
          "caption":
            "Right column, between battles: three calls; the two specialists read this battle's public record; only the cavalry's graph changed.",
          "message": {
            "example": "methods-gap",
            "key": "revision"
          },
          "refs": [
            "src/twwarhammer3/battle/graph_author.py:175-179",
            "runs/twwarhammer3/gap-20261101/revised-01/manifest.json"
          ]
        }
      ]
    }
  ]
});
