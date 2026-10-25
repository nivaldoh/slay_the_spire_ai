checkpoint_siege = {orders = {}, controllers = {}}
local aa = bm:alliances():item(ATTACK_SIDE):armies():item(1)
local buildings = bm.battle:buildings()
local gate, wall
local p = aa:units():item(5):position()
local best = 1e30
for i = 1, buildings:count() do
  local b = buildings:item(i)
  if b:has_gate() then gate = b end
  if b:is_fort_wall() and not b:has_gate() then
    local q = b:central_position()
    local distance = (p:get_x()-q:get_x())^2 + (p:get_z()-q:get_z())^2
    if distance < best then wall, best = b, distance end
  end
end
assert(gate and wall, 'missing siege gate/wall')
bm:callback(function()
  for _, item in ipairs({{2, gate}, {5, wall}}) do
    local c = aa:create_unit_controller(); c:add_units(aa:units():item(item[1])); c:take_control()
    c:besiege_building(item[2], 1, true)
    checkpoint_siege.controllers[#checkpoint_siege.controllers + 1] = c
    checkpoint_siege.orders[#checkpoint_siege.orders + 1] = {unit=item[1], building=item[2]:name()}
  end
  local c = aa:create_unit_controller(); c:add_units(aa:units():item(8)); c:take_control()
  assert(aa:units():item(8):type() == 'wh_main_emp_art_great_cannon')
  c:attack_building(gate, 1, false)
  checkpoint_siege.controllers[#checkpoint_siege.controllers + 1] = c
end, 10000, 'siege_assault')
return twwarhammer3_json.encode({ms=bm.battle:time_elapsed_ms()})
