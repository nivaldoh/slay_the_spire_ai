"""What the two-front defence's witness and its readings both use (ksl-nor-lines-a-v1, -b-v1): the
unit type keys, the line's types and the relief trigger. lines.py and lines_readings.py import
these; the readings never import the witness (tests/test_repo_rules.py; owner, 2026-11-15).
"""

KOSSARS = "wh3_main_ksl_inf_kossars_1"
ARMOURED = "wh3_main_ksl_inf_armoured_kossars_0"
STRELTSI = "wh3_main_ksl_inf_streltsi_0"
GUARD = "wh3_main_ksl_inf_tzar_guard_0"
BOYAR = "wh3_main_ksl_cha_boyar_0"
LANCERS = "wh3_main_ksl_cav_winged_lancers_0"
LINE = (KOSSARS, ARMOURED, STRELTSI)

# The relief trigger. The values rest on JUDGEMENT src/twwarhammer3/battle/lines.py Lines witness
# rules.
AHEAD_M = 60  # an enemy first seen this far ahead of the outer line is a relief unit
TRIGGER_UNITS = 6  # W and M choose a side once this many enemies stand that far ahead
