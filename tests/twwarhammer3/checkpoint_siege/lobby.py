"""Exact Empire siege equipment for the checkpoint probes; no game launch.

Insert these steps after army recruitment and before the start-battle click. Counts and
the attacking lobby slot are supplied by each recorded test case, with no defaults.
Commands mirror ui3.pack's custom_battle.twui.xml equipment callbacks. The installed
custom-battle DB cap fields differ from the live RecruitmentCap (-1 in the first probe).
CanAddSiegeEquipment and the slot's total capacity decide whether a request is legal.
"""


def make_lobby_steps(rams, towers, attacker_slot):
    """Clear the slot's existing equipment, then require exactly the requested counts."""
    for name, count, maximum in (("rams", rams, 2), ("towers", towers, 10)):
        if type(count) is not int or not 0 <= count <= maximum:
            raise ValueError(f"{name} must be an integer from 0 to {maximum}")
    if type(attacker_slot) is not int or attacker_slot < 0:
        raise ValueError("attacker_slot must be a nonnegative lobby slot index")

    lobby = "CustomBattleLobbyContext."
    slot = f"{lobby}PlayerSlotList.At({attacker_slot})."
    equipment = (("emp_battering_ram", rams, 2), ("emp_siege_tower_15m", towers, 10))

    def read(expression, expect=None):
        step = {"context": "CcoFrontendRoot", "expression": expression, "required": True}
        if expect is not None:
            step.update(expect=expect, timeout_ms=15000)
        return step

    def command(expression, **extra):
        return {"context": "CcoFrontendRoot", "command": expression, "required": True, **extra}

    steps = [
        {"log": f"siege equipment: attacker slot {attacker_slot}, rams {rams}, towers {towers}"},
        read(lobby + f"PlayerSlotList.Size > {attacker_slot}", True),
        read(lobby + "SettingsContext.IsSiegeBattleType", True),
        read(slot + "TeamContext.IsAttacker", True),
        read(slot + "CanModifyUnits", True),
        read(slot + 'AvailableSiegeEquipmentList.JoinString(Key + "|" + RecruitmentCap + "|" '
             '+ Cost + "|" + Uses15mWall + "|" + Uses8mWall, ";")'),
        read(slot + "NumSiegeVehiclesAvailable"),
        read(slot + 'SiegeEquipmentList.JoinString(Key, ";")'),
        read(slot + 'SiegeEquipmentList.Count(Key != "emp_battering_ram" '
             '&& Key != "emp_siege_tower_15m")', 0),
    ]
    for key, count, maximum in equipment:
        selected = slot + f'SiegeEquipmentList.Count(Key == "{key}")'
        # Clear only the two known Empire types within this helper's supported counts;
        # the subsequent zero readback rejects a failed or incomplete removal.
        steps.append(read(selected + f" <= {maximum}", True))
        for _ in range(maximum):
            steps.append(command(slot + "RemoveSiegeEquipment(" + slot
                                 + f'SiegeEquipmentList.FirstContext(Key == "{key}"))',
                                 when=selected + " > 0"))
        steps.append(read(selected, 0))
        if count:
            steps.append(read(slot + f'AvailableSiegeEquipmentList.Count(Key == "{key}")', 1))

    steps += [read(slot + "SiegeEquipmentList.Size", 0),
              read(slot + f"NumSiegeVehiclesAvailable >= {rams + towers}", True)]
    for key, count, _ in equipment:
        selected = slot + f'SiegeEquipmentList.Count(Key == "{key}")'
        available = slot + f'AvailableSiegeEquipmentList.FirstContext(Key == "{key}")'
        for number in range(1, count + 1):
            steps += [read(slot + f"CanAddSiegeEquipment({available})", True),
                      command(slot + f"AddSiegeEquipment({available})"),
                      read(selected, number)]
        steps.append(read(selected, count))
    steps += [read(slot + "SiegeEquipmentList.Size", rams + towers),
              read(slot + 'SiegeEquipmentList.JoinString(Key, ";")'),
              read(slot + "NumSiegeVehiclesAvailable - " + slot + "SiegeEquipmentList.Size")]
    return steps
