"""Proposed component checks: preserve the recorded inbox, caveats and source links.

These checks do not establish that the snapshot is live or that it reduces review time.
"""

import importlib.util
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("project_overview",
                                              ROOT / "scripts/project_overview.py")
overview = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(overview)


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.text, self.links, self.ids, self.decisions, self.open_decisions = [], [], [], 0, 0
        self.feed(text)

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if "id" in attributes:
            self.ids.append(attributes["id"])
        if tag == "a":
            self.links.append(attributes["href"])
        if tag == "details" and attributes.get("class") == "decision":
            self.decisions += 1
            self.open_decisions += "open" in attributes

    def handle_data(self, data):
        self.text.append(data)


def document():
    return """# Project state

Updated 2026-10-22: recorded state.

## Active work

WH3 first. No job is recorded as running.

Component checks passed at `old-tip`; live behavior remains unverified at the new tip.

## Total War: WARHAMMER III

The model team is on a branch.

See the [team notes](twwarhammer3/team.md#results) and [branches](#branches).

## Slay the Spire

Paused; no run has won.

## Post-training

No learning claim.

## Owner decisions waiting

1. **Benchmark rules.** Choose the remaining gates.

   The witness timing is already agreed; keep c1 unchanged.
2. **Next experiment.** Choose a free night, not a new scoring rule.

   The screen scope is agreed. $10 is an estimate, not authorization.
3. **Autonomy.** Accept or revise the proposal.
4. **Training.** Choose a host later.

## Known issues

- Slow-team costs are under-counted.
- A timer win alone is insufficient.

## Branches

- `model-team`: offline evidence only.

## Runtime and ownership

Existing permissions only.
"""


def render(text):
    return overview.render(text, ROOT / "docs/state.md", ROOT / "runs/project-overview/index.html",
                           datetime(2026, 10, 22, 12, 0, tzinfo=UTC))


def test_preserves_all_topics_evidence_limits_and_links_including_collapsed_content():
    page = Page(render(document()))
    prose = " ".join(page.text)
    assert page.decisions == 4 and page.open_decisions == 3
    for expected in ("Choose the remaining gates.", "Choose a host later.",
                     "The witness timing is already agreed; keep c1 unchanged.",
                     "$10 is an estimate, not authorization.",
                     "live behavior remains unverified at the new tip.",
                     "Slow-team costs are under-counted."):
        assert expected in prose
    assert "sources/docs/twwarhammer3/team.html#results" in page.links
    assert "#branches" in page.links and "branches" in page.ids
    assert all(href[1:] in page.ids for href in page.links if href.startswith("#"))


def test_rebuilding_changes_recorded_content_and_does_not_interpret_source_html():
    original = render(document())
    revised = render(document().replace("Choose a host later.", "<script>window.paid()</script>"))
    assert "Choose a host later." in original and "Choose a host later." not in revised
    assert "<script>" not in revised and "&lt;script&gt;window.paid()&lt;/script&gt;" in revised
    assert "Snapshot, not live status" in revised and "2026-10-22 12:00 UTC" in revised
    malicious = document().replace("[branches](#branches)", "[branches](javascript:paid)")
    assert "javascript:" not in render(malicious)


def test_missing_or_unrecognized_inbox_is_reported_instead_of_showing_no_decisions():
    with pytest.raises(ValueError, match="missing sections: Owner decisions waiting"):
        render(document().replace("## Owner decisions waiting", "## Decisions"))
    with pytest.raises(ValueError, match="needs numbered topics"):
        render(document().replace("1. **Benchmark rules.**", "- **Benchmark rules.**"))
    with pytest.raises(ValueError, match="needs numbered topics"):
        render(document().replace("3. **Autonomy.**", "- **Autonomy.**"))
    with pytest.raises(ValueError, match="needs numbered topics"):
        render(document().replace(document().split("## Owner decisions waiting\n\n")[1]
                                  .split("## Known issues")[0], ""))
    empty = document().split("## Owner decisions waiting")[0] + (
        "## Owner decisions waiting\n\nNone.\n\n## Known issues\n\nNo known issues.\n\n"
        "## Branches\n\nNone.\n\n## Runtime and ownership\n\nExisting permissions only.")
    assert Page(render(empty)).decisions == 0
    assert "No decisions recorded." in render(empty)
