"""C's communication declaration preserves its fixed native-AI battle.

Reference: communication-structure.md, The battle: Cannae C, and Later expansions;
cannae-communication.md, Battle construction. A reserve intervention is a later variant,
and the current comparison uses the engine outcome rather than a custom objective.
The local_team.py refusal sweep found this refusal unexercised by its focused tests.
No runtime behavior, scenario, existing assertion or verification rule changes here.
"""

from copy import deepcopy

import pytest

from twwarhammer3.battle import local_team, setup


@pytest.mark.parametrize("name", ("emp-envelopment-c-v1", "emp-envelopment-c-peer-v2"))
@pytest.mark.parametrize("field", ("reserve", "custom"))
def test_c_rejects_an_intervention_before_accepting_its_communication_arm(name, field):
    scenarios = setup.scenarios()
    candidate = deepcopy(scenarios[name])
    # Use an existing intervention declaration, without executing it or creating a scenario.
    candidate[field] = deepcopy(next(row[field] for row in scenarios.values() if row.get(field)))
    with pytest.raises(ValueError, match="native AI without a custom objective or reserve"):
        local_team.declaration(candidate)
