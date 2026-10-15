-- Optional presentation evidence. The caller supplies only public unit positions.
-- Nothing here submits orders or changes battle speed. Camera registration is unverified.
local evidence, seen, last_capture, last_second = nil, {}, -30000, nil
local previous = {}
local deferred_action
local BRIDGE = "C:/wh3-agent/bridge/"

local function save()
    local path = BRIDGE .. "imagery-" .. evidence.battle .. ".json"
    local file = assert(io.open(path .. ".tmp", "w"))
    file:write(twwarhammer3_json.encode(evidence))
    file:close()
    os.remove(path)
    assert(os.rename(path .. ".tmp", path))
end

local function xyz(vector)
    return {vector:get_x(), vector:get_y(), vector:get_z()}
end

local function has(unit, flag)
    for _, value in ipairs(unit.state or {}) do if value == flag then return true end end
    return false
end

local function centre(units)
    local x, z = 0, 0
    for _, unit in ipairs(units) do x, z = x + unit.x, z + unit.z end
    return {x = x / #units, z = z / #units}
end

-- Connected groups within 80 m; choose the group containing the most melee units.
local function action_centre(units, trigger)
    local melee, used, largest = {}, {}, {}
    if trigger == "incoming_fire" then
        local targets = {}
        for _, unit in ipairs(units) do if has(unit, "under_fire") then targets[#targets + 1] = unit end end
        if #targets > 0 then return centre(targets) end
    end
    for _, unit in ipairs(units) do if has(unit, "melee") then melee[#melee + 1] = unit end end
    for index, unit in ipairs(melee) do
        if not used[index] then
            local group, cursor = {unit}, 1
            used[index] = true
            while cursor <= #group do
                local from = group[cursor]
                for other, target in ipairs(melee) do
                    if not used[other] and (from.x - target.x)^2 + (from.z - target.z)^2 <= 80^2 then
                        used[other] = true
                        group[#group + 1] = target
                    end
                end
                cursor = cursor + 1
            end
            if #group > #largest then largest = group end
        end
    end
    return centre(#largest > 0 and largest or units)
end

-- Both members must be visible now and on the preceding sample. A closing gap
-- describes observed motion; it does not imply a charge order or intention.
local function approach_pair(frame)
    local closest, distance
    for _, friendly in ipairs(frame.friendly or {}) do
        for _, enemy in ipairs(frame.enemy or {}) do
            if friendly.x and friendly.z and enemy.x and enemy.z
                and (friendly.men or 0) > 0 and (enemy.men or 0) > 0
                and not has(friendly, "routing") and not has(enemy, "routing") then
                local gap = math.sqrt((friendly.x - enemy.x)^2 + (friendly.z - enemy.z)^2)
                local before_f, before_e = previous[friendly.id], previous[enemy.id]
                if gap <= 100 and before_f and before_e then
                    local before = math.sqrt((before_f.x - before_e.x)^2 + (before_f.z - before_e.z)^2)
                    if before - gap >= 1 and (not distance or gap < distance) then
                        closest, distance = {friendly, enemy}, gap
                    end
                end
            end
        end
    end
    return closest, distance
end

local function capture(trigger, frame, units, pair, distance, deferred)
    local target = trigger == "opening" and centre(units) or pair and centre(pair) or action_centre(units, trigger)
    local shot = {trigger = trigger, trigger_time_ms = frame.time_ms, status = "pending",
        policy_input = false, visibility = "Visibility not audited; may show units hidden from the controller.",
        projection = "unregistered; use the public passability grid for positions"}
    if pair then
        shot.focus_units, shot.distance_m = {pair[1].id, pair[2].id}, distance
        shot.caption = "Visible opposing units closing within 100 m, before observed melee."
    end
    if deferred then
        shot.deferred_from = {trigger = evidence.stills[deferred].trigger, time_ms = evidence.stills[deferred].time_ms}
        shot.caption = (shot.caption or "") .. " Capture deferred to maintain 30 s spacing."
        evidence.stills[deferred] = shot
    else
        evidence.stills[#evidence.stills + 1] = shot
    end
    local began = os.clock()
    local ok, err = pcall(function()
        local ground = bm.battle:get_terrain_height(target.x, target.z)
        local opening = trigger == "opening"
        local dx, dz = 0, 1
        if pair and distance > 0 then
            dx, dz = (pair[2].x - pair[1].x) / distance, (pair[2].z - pair[1].z) / distance
        end
        local back, side = opening and 0.1 or math.max(65, (distance or 0) * 1.1), opening and 0 or 30
        local x, z = target.x - dx * back + dz * side, target.z - dz * back - dx * side
        local height = opening and ground + 500 or math.max(ground + 28, bm.battle:get_terrain_height(x, z) + 8)
        local position = v(x, height, z)
        local look = v(target.x, ground + (opening and 0 or 3), target.z)
        local fov = opening and 45 or 55
        shot.requested_camera = {position = xyz(position), target = xyz(look), fov = fov}
        -- The ordinary camera clamps both altitude and pitch. This affects only
        -- the view: no cutscene, pause, input events or unit-control changes.
        bm.battle:enable_cinematic_camera(true)
        bm:camera():move_to(position, look, 0, true, fov)
    end)
    shot.camera_cpu_ms = (os.clock() - began) * 1000
    if not ok then shot.status, shot.error = "capture_failed", tostring(err); save(); return end
    save()
    -- Let the renderer show the requested view. No sleep or wait on the order path.
    local callback = "wh3_still_" .. trigger
    bm:repeat_real_callback(function()
        bm:remove_real_callback(callback)
        local good, problem = pcall(function()
            shot.time_ms = bm.battle:time_elapsed_ms()
            shot.camera = {position = xyz(bm:camera():position()), target = xyz(bm:camera():target())}
            shot.status = "capture_ready"
            shot.backend = "passive_windows_pillow"
        end)
        if not good then shot.status, shot.error = "capture_failed", tostring(problem) end
        pcall(save)
    end, 500, callback)
end

function twwarhammer3_imagery(frame, names)
    if not evidence then
        evidence = {version = 3, job = frame.job, battle = frame.battle, names = names or {},
            stills = {}, policy_input = false}
        save()
    end
    local second = math.floor(frame.time_ms / 1000)
    if second == last_second and not frame.terminal then return end
    last_second = second
    local units, contact, rout, under_fire = {}, false, false, false
    for _, side in ipairs({"friendly", "enemy"}) do
        for _, unit in ipairs(frame[side] or {}) do
            if unit.x and unit.z and (unit.men or 0) > 0 then
                units[#units + 1] = unit
                contact = contact or has(unit, "melee")
                rout = rout or has(unit, "routing")
                under_fire = under_fire or side == "friendly" and has(unit, "under_fire")
            end
        end
    end
    if #units == 0 then
        previous = {}
        if frame.terminal and not seen.ending then
            seen.ending = true
            evidence.stills[#evidence.stills + 1] = {trigger = "ending", time_ms = frame.time_ms,
                status = "capture_failed", error = "No public live positions to aim the camera"}
            save()
        end
        return
    end
    local pair, distance = approach_pair(frame)
    previous = {}
    for _, unit in ipairs(units) do if unit.id then previous[unit.id] = {x = unit.x, z = unit.z} end end
    -- One action slot, so earlier views replace first melee rather than add images.
    local action = not seen.action and (not contact and pair and "approach"
        or under_fire and "incoming_fire" or contact and "first_contact")
    local trigger = not seen.opening and "opening" or frame.terminal and not seen.ending and "ending"
        or action or rout and not seen.first_rout and "first_rout"
    if not trigger then return end
    seen[trigger] = true
    if frame.time_ms - last_capture < 30000 and not frame.terminal then
        if trigger ~= action or not deferred_action then
            evidence.stills[#evidence.stills + 1] = {trigger = trigger, time_ms = frame.time_ms,
                status = "throttled", error = "Within 30 battle seconds of the preceding still"}
            if trigger == action then deferred_action = #evidence.stills end
            save()
        end
        return
    end
    if trigger == action then seen.action = true end
    last_capture = frame.time_ms
    capture(trigger, frame, units, trigger == "approach" and pair or nil,
        trigger == "approach" and distance or nil, trigger == action and deferred_action or nil)
end
