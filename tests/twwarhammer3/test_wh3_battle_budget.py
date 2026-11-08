"""A battle allowance shared by members that call from their own threads."""

import threading

import pytest

from gameai.ledger import BudgetExhausted, Ledger
from twwarhammer3.battle import benchmark


class MeetingLedger(Ledger):
    """Holds each reservation until the other member also reaches it, or the wait times out."""

    def __init__(self, path, budget_usd):
        super().__init__(path, budget_usd)
        self.meeting = threading.Barrier(2, timeout=.5)

    def reserve(self, usd):
        try:
            self.meeting.wait()
        except threading.BrokenBarrierError:
            pass  # the other member never got this far
        super().reserve(usd)


# ClassTeam members share one budget; direct model leaves each get their own on one ledger.
@pytest.mark.parametrize("shared", [True, False], ids=["one-budget", "budget-per-member"])
def test_members_calling_at_once_cannot_reserve_past_the_battle_allowance(tmp_path, shared):
    ledger = MeetingLedger(tmp_path / "spend", 100)
    budgets = [benchmark.suite_budget(ledger)] * 2 if shared else [
        benchmark.suite_budget(ledger), benchmark.suite_budget(ledger)]
    ledger.charge(2.99, reason="this battle so far")
    results = []

    def call(budget):
        try:
            budget.reserve(.009)
        except BudgetExhausted as error:
            results.append(str(error))
            return
        budget.charge(.009, estimated=True)
        budget.release(.009)
        results.append("sent")

    threads = [threading.Thread(target=call, args=(budget,)) for budget in budgets]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(5)
    assert not any(thread.is_alive() for thread in threads)
    assert sorted(results) == ["Benchmark next call exceeds $3 battle allowance", "sent"]
    assert ledger.spent == pytest.approx(2.999)
    assert ledger.held == pytest.approx(0)
