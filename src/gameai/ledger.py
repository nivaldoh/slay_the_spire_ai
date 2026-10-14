"""Append-only spend ledgers with a hard budget, for every track that pays per call.

Each game keeps its own file (its package names the path), and every job naming the
same file shares one budget. A caller reserves a call's worst-case cost before sending
it and charges the reported cost after.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


class BudgetExhausted(RuntimeError):
    """The next call could exceed the declared spend budget; nothing was sent."""


class Ledger:
    """Append-only spend record; every job naming the same file shares one budget."""

    def __init__(self, path: Path, budget_usd: float):
        self.path = Path(path)
        self.budget = budget_usd
        lines = self.path.read_text().splitlines() if self.path.exists() else []
        self.spent = sum(json.loads(line)["usd"] for line in lines)

    def reserve(self, usd: float) -> None:
        if self.spent + usd > self.budget:
            raise BudgetExhausted(
                f"Spent ${self.spent:.4f} of ${self.budget:.2f}; next call may cost ${usd:.4f}"
            )

    def charge(self, usd: float, **fields) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {"time": datetime.now(UTC).isoformat(), "usd": usd, **fields}
        with self.path.open("a") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        self.spent += usd
