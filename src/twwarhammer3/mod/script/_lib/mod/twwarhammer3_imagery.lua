-- Optional presentation evidence. The caller supplies only public unit positions.
-- Nothing here submits orders or changes battle speed. Camera registration is unverified.
local evidence, seen, last_capture, last_second = nil, {}, -30000, nil
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
local function action_centre(units)
    local melee, used, largest = {}, {}, {}
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

local function capture(trigger, frame, units)
    local target = trigger == "opening" and centre(units) or action_centre(units)
    local shot = {trigger = trigger, trigger_time_ms = frame.time_ms, status = "pending",
        policy_input = false, visibility = "Visibility not audited; may show units hidden from the controller.",
        projection = "unregistered; use the public passability grid for positions"}
    evidence.stills[#evidence.stills + 1] = shot
    local began = os.clock()
    local ok, err = pcall(function()
        local ground = bm.battle:get_terrain_height(target.x, target.z)
        local opening = trigger == "opening"
        local position = v(target.x, ground + (opening and 500 or 180), target.z - (opening and 0.1 or 80))
        local look = v(target.x, ground, target.z)
        shot.requested_camera = {position = xyz(position), target = xyz(look), fov = 45}
        bm:camera():move_to(position, look, 0, true, 45)
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
            shot.file = "still-" .. evidence.battle .. "-" .. trigger .. ".tga"
            local start = os.clock()
            common.take_screenshot(BRIDGE .. shot.file)
            shot.capture_cpu_ms = (os.clock() - start) * 1000
            shot.after_capture_ms = bm.battle:time_elapsed_ms()
            shot.status = "capture_requested"
        end)
        if not good then shot.status, shot.error = "capture_failed", tostring(problem) end
        pcall(save)
    end, 500, callback)
end

function twwarhammer3_imagery(frame, names)
    if not evidence then
        evidence = {version = 1, job = frame.job, battle = frame.battle, names = names or {},
            stills = {}, policy_input = false}
        save()
    end
    local second = math.floor(frame.time_ms / 1000)
    if second == last_second and not frame.terminal then return end
    last_second = second
    local units, contact, rout = {}, false, false
    for _, side in ipairs({"friendly", "enemy"}) do
        for _, unit in ipairs(frame[side] or {}) do
            if unit.x and unit.z and (unit.men or 0) > 0 then
                units[#units + 1] = unit
                contact = contact or has(unit, "melee")
                rout = rout or has(unit, "routing")
            end
        end
    end
    if #units == 0 then
        if frame.terminal and not seen.ending then
            seen.ending = true
            evidence.stills[#evidence.stills + 1] = {trigger = "ending", time_ms = frame.time_ms,
                status = "capture_failed", error = "No public live positions to aim the camera"}
            save()
        end
        return
    end
    local trigger = not seen.opening and "opening" or frame.terminal and not seen.ending and "ending"
        or contact and not seen.first_contact and "first_contact" or rout and not seen.first_rout and "first_rout"
    if not trigger then return end
    seen[trigger] = true
    if frame.time_ms - last_capture < 30000 and not frame.terminal then
        evidence.stills[#evidence.stills + 1] = {trigger = trigger, time_ms = frame.time_ms,
            status = "throttled", error = "Within 30 battle seconds of the preceding still"}
        save()
        return
    end
    last_capture = frame.time_ms
    capture(trigger, frame, units)
end
