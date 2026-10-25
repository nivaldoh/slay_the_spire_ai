local attackers=bm:alliances():item(ATTACK_SIDE):armies():item(1)
local defenders=bm:alliances():item(3-ATTACK_SIDE):armies():item(1)
bm:callback(function()
  local cavalry
  for i=1,defenders:units():count() do
    local u=defenders:units():item(i)
    if u:type()=='wh_main_emp_cav_empire_knights' then cavalry=u; break end
  end
  assert(cavalry,'no defending cavalry')
  local p=attackers:units():item(2):position()
  local c=defenders:create_unit_controller(); c:add_units(cavalry); c:take_control()
  c:goto_location(v(p:get_x(),bm.battle:get_terrain_height(p:get_x(),p:get_z()),p:get_z()),true)
  checkpoint_controllers=checkpoint_controllers or {}
  checkpoint_controllers[#checkpoint_controllers+1]=c
end,15000,'checkpoint_exit_gate')
return twwarhammer3_json.encode({installed=true})
