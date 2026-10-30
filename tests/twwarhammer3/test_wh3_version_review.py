"""The ending of .claude/workflows/wh3-version-review.js, run by Node with agent() stubbed: a step
that returns nothing, or a judge whose pick names no candidate, makes the run incomplete, and no
judge means no proposal (light factory plan, B8). The prompts and the real Workflow runtime are
not exercised."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

WORKFLOW = Path(__file__).resolve().parents[2] / ".claude" / "workflows" / "wh3-version-review.js"
RUN = r"""
const fs = require('node:fs');
const [path, mode] = process.argv.slice(2);
const source = fs.readFileSync(path, 'utf8').replace('export const meta', 'const meta');
const body = new (async () => {}).constructor('args', 'agent', 'parallel', 'phase', 'log', source);
const agent = async (prompt, { label }) => {
  if (label.startsWith('review:'))
    return mode === 'no review' && label.endsWith('0000') ? null
      : { outcome: 'lost', summary: 's', mistakes: [], good: [], harness_issues: [] };
  if (label.startsWith('propose:'))
    return mode === 'no proposer' && label === 'propose:tactics' ? null
      : { title: label, change: 'c', evidence: 'e', expected_effect: 'x', risks: 'r' };
  if (mode === 'none') return null;
  return { scores: [], pick: mode === 'no match' ? 'no change' : 'propose:information' };
};
body({ job: 'runs/j', episodes: ['episode-0000', 'episode-0001'] }, agent,
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


@pytest.mark.parametrize("mode,missing", [
    ("no review", ["review:runs/j/episode-0000"]),  # the first: not the last
    ("no proposer", ["propose:tactics"]),
])
def test_a_review_or_proposal_that_returns_nothing_makes_the_run_incomplete(mode, missing):
    assert run(mode) == {"status": "incomplete", "missing": missing,
                         "proposal": "propose:information"}


def test_judges_whose_pick_names_no_candidate_count_as_missing():
    # "no change" is not the candidate's title ("No change"): before, the first candidate won
    assert run("no match") == {"status": "incomplete", "proposal": None,
                               "missing": ["judge:1", "judge:2", "judge:3"]}
