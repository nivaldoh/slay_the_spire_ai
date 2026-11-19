"""What the camp attack's witness and its readings both use (emp-chd-camp-v1): the unit groups by
type key and the cue rule. camp.py and camp_readings.py import these; the readings never import
the witness (tests/test_repo_rules.py; owner, 2026-11-15, "F1: readings off witnesses").
"""

# Groups by the scenario's type keys. They rest on JUDGEMENT src/twwarhammer3/scenarios/camp.py
# Camp groups.
MOUNTED = {"wh_main_emp_cha_general_1": 1, "wh_main_emp_cav_empire_knights": 2,
           "wh_main_emp_cav_reiksguard": 1}
LEVIES = {"wh_main_emp_cha_warrior_priest_0": 1, "wh_dlc04_emp_inf_flagellants_0": 3,
          "wh_dlc04_emp_inf_free_company_militia_0": 2}
COVER = {"wh3_dlc23_chd_cav_hobgoblin_wolf_raiders_spears", "wh3_dlc23_chd_cav_bull_centaurs_axe"}
GUNS = {"wh3_dlc23_chd_veh_magma_cannon", "wh3_dlc23_chd_veh_deathshrieker_rocket_launcher"}

# The cue: one cover unit in melee within CUE_M of a levy for CUE_HOLD_MS, else FALLBACK_MS. The
# values rest on JUDGEMENT src/twwarhammer3/scenarios/camp.py Camp thresholds.
CUE_M = 30
CUE_HOLD_MS = 10000
FALLBACK_MS = 180000
