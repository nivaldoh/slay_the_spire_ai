local a = bm:alliances():item(1):armies():item(1)
local u, t = a:units():item(1), a:units():item(2)
local key = 'wh_main_spell_metal_glittering_robe'
assert(u:type() == 'wh_main_emp_cha_balthasar_gelt_1', u:type())
local c = a:create_unit_controller(); c:add_units(u); c:take_control()
c:perform_special_ability(key, t)
checkpoint_controllers = checkpoint_controllers or {}
checkpoint_controllers[#checkpoint_controllers + 1] = c
return twwarhammer3_json.encode({caster=u:type(), target=t:type(), key=key,
  ms=bm.battle:time_elapsed_ms()})
