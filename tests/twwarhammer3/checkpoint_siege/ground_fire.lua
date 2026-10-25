-- JUDGEMENT: Codex, 2026-10-25: ground fire creates an ammo-spent checkpoint state
-- instead of waiting for a natural shot; this fixture makes no battle-strength claim.
local a = bm:alliances():item(1):armies():item(1)
local cannon = a:units():item(8)
assert(cannon:type() == "wh_main_emp_art_great_cannon", "expected friendly cannon at index 8")
local p = cannon:position()
local enemy = bm:alliances():item(2):armies():item(1):units():item(1):position()
local dx, dz = enemy:get_x() - p:get_x(), enemy:get_z() - p:get_z()
local distance = math.sqrt(dx * dx + dz * dz)
assert(distance >= 100, "enemy general must be at least 100m from cannon")
local x, z = p:get_x() + dx * 100 / distance, p:get_z() + dz * 100 / distance
local corners = {bm.battle:battle_boundaries()}
assert(#corners >= 2, "battle boundaries missing")
local min_x, max_x = corners[1]:get_x(), corners[1]:get_x()
local min_z, max_z = corners[1]:get_z(), corners[1]:get_z()
for _, corner in ipairs(corners) do
    min_x, max_x = math.min(min_x, corner:get_x()), math.max(max_x, corner:get_x())
    min_z, max_z = math.min(min_z, corner:get_z()), math.max(max_z, corner:get_z())
end
assert(x >= min_x and x <= max_x and z >= min_z and z <= max_z, "ground target outside bounds")
local y = bm.battle:get_terrain_height(x, z)
local ammo_before = cannon:ammo_left()
local c = a:create_unit_controller()
c:add_units(cannon)
c:take_control()
c:attack_location(v(x, y, z), false)
checkpoint_controllers = checkpoint_controllers or {}
checkpoint_controllers[#checkpoint_controllers + 1] = c
return twwarhammer3_json.encode({ms = bm.battle:time_elapsed_ms(), ammo_before = ammo_before,
                               target = {x = x, y = y, z = z}})
