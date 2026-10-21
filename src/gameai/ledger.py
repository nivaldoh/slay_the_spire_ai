"""Append-only spend ledgers with a hard budget, for every track that pays per call.

Each game keeps its own file (its package names the path), and every job naming the
same file shares one budget. A caller reserves a call's worst-case cost before sending
it, charges the reported cost after and then releases the reservation. Reservations of
calls still in flight count against the budget, so concurrent calls cannot overspend it.
"""

from __future__ import annotations

import json
import math
import threading
from datetime import UTC, datetime
from pathlib import Path


class BudgetExhausted(RuntimeError):
    """The next call could exceed the declared spend budget; nothing was sent."""


class Ledger:
    """Append-only spend record; every job naming the same file shares one budget."""

    def __init__(self, path: Path, budget_usd: float, *, must_exist: bool = False):
        if not math.isfinite(budget_usd) or budget_usd < 0:
            raise ValueError("Budget must be finite and nonnegative")
        self.path = Path(path)
        if must_exist and not self.path.is_file():
            # A mistyped path, or a job started from a worktree, would start at $0 spent.
            raise FileNotFoundError(f"No spend ledger at {self.path}; create the file to"
                                    " start a new ledger deliberately")
        self.budget = budget_usd
        lines = self.path.read_text().splitlines() if self.path.exists() else []
        self.spent = sum(json.loads(line)["usd"] for line in lines)
        self.held = 0.0
        self._lock = threading.Lock()

    def reserve(self, usd: float) -> None:
        if not math.isfinite(usd) or usd < 0:
            raise ValueError("Reservation must be finite and nonnegative")
        with self._lock:
            if self.spent + self.held + usd > self.budget:
                held = f" (${self.held:.4f} held by calls in flight)" if self.held else ""
                raise BudgetExhausted(f"Spent ${self.spent:.4f} of ${self.budget:.2f}{held};"
                                      f" next call may cost ${usd:.4f}")
            self.held += usd

    def release(self, usd: float) -> None:
        with self._lock:
            self.held -= usd

    def charge(self, usd: float, **fields) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {"time": datetime.now(UTC).isoformat(), "usd": usd, **fields}
        with self._lock:
            with self.path.open("a") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
            self.spent += usd
