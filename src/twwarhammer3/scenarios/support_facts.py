"""Regiment identities shared by the support timing policies and evidence reader."""

from twwarhammer3.protocol import ProtocolError

TYPES = {"infantry": "wh_main_emp_inf_swordsmen", "cavalry": "wh_main_emp_cav_empire_knights",
         "enemy": "wh_main_emp_inf_greatswords"}


def identities(observation):
    """Bind by type, never recruitment order. Missing/duplicate identity is a defect."""
    result = {}
    for role, kind in TYPES.items():
        side = "enemy_roster" if role == "enemy" else "friendly"
        matches = [u for u in observation.get(side, []) if u.get("type") == kind]
        if len(matches) != 1 or not matches[0].get("id"):
            raise ProtocolError(f"support timing: ambiguous {role} identity")
        result[role] = matches[0]["id"]
    if len(set(result.values())) != 3:
        raise ProtocolError("support timing: duplicate unit IDs")
    return result
