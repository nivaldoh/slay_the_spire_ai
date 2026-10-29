"""The ending of .claude/workflows/wh3-version-review.js, run by Node with agent() stubbed: a step
that returns nothing makes the run incomplete, and no judge means no proposal (light factory
plan, B8). The prompts and the real Workflow runtime are not exercised."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

WORKFLOW = Path(__file__).resolve().parents[2] / ".claude" / "workflows" / "wh3-version-review.js"
RUN = r"""
const fs = require('node:fs');
const [path, judged] = process.argv.slice(2);
const source = fs.readFileSync(path, 'utf8').replace('export const meta', 'const meta');
const body = new (async () => {}).constructor('args', 'agent', 'parallel', 'phase', 'log', source);
const agent = async (prompt, { label }) => {
  if (label.startsWith('review:'))
    return { outcome: 'lost', summary: 's', mistakes: [], good: [], harness_issues: [] };
  if (label.startsWith('propose:'))
    return { title: label, change: 'c', evidence: 'e', expected_effect: 'x', risks: 'r' };
  return judged === 'none' ? null : { scores: [], pick: 'propose:information' };
};
body({ job: 'runs/j', episodes: ['episode-0000'] }, agent,
     fns => Promise.all(fns.map(f => f())), () => {}, () => {})
  .then(r => console.log(JSON.stringify({ status: r.status, missing: r.missing,
                                          proposal: r.proposal })));
"""


def run(judged: str) -> dict:
    node = shutil.which("node")
    if node is None:
        pytest.skip("needs Node.js")
    result = subprocess.run([node, "-", str(WORKFLOW), judged], input=RUN, capture_output=True,
                            text=True, check=True)
    return json.loads(result.stdout)


def test_a_review_without_judges_is_incomplete_and_proposes_nothing():
    assert run("none") == {"status": "incomplete", "proposal": None,
                           "missing": ["judge:1", "judge:2", "judge:3"]}


def test_a_complete_review_returns_the_judges_pick_as_a_proposal():
    assert run("all") == {"status": "complete", "missing": [], "proposal": "propose:information"}
