-- twwarhammer3_battle.lua: the in-game side of the twwarhammer3 harness (Lua 5.1).
--
-- The vanilla mod loader runs this file from script/battle/mod/ when a battle's script
-- libraries load, after `bm` exists. It stays inert unless C:/wh3-agent/bridge/session.json
-- enables it. Then it publishes observation.json on model time, polls orders.json on UI
-- time, applies orders through one unit controller per
-- friendly unit, and reports the result. engine/mailbox.py documents the messages.

local BRIDGE = "C:/wh3-agent/bridge/"
local REMATCH = {"in_battle_results_popup", "button_rematch"}
local CONFIRM = {"dialogue_box", "both_group", "button_tick"}
local json = twwarhammer3_json
local ui = twwarhammer3_ui

local state = {
    battle = nil, seq = 0, started = false, finished = false, result = nil,
    friendly = {}, friendly_ids = {}, enemy = {}, enemy_ids = {}, enemy_by_ui = {},
    pending = nil, last_request = nil, applied = nil, applied_ms = nil,
    next_observe_ms = 0, force_observe = false, alliance = nil,
    army_abilities = {}, army_issued = {}, known = {}, info = {},
}
local session = nil
local BEHAVIOURS = {"fire_at_will", "skirmish", "defend", "change_formation_spacing", "formed_attack"}

local function read_file(path)
    local file = io.open(path, "r")
    if not file then return nil end
    local text = file:read("*a")
    file:close()
    return text
end

local function read_json(path)
    local text = read_file(path)
    if not text or text == "" then return nil end
    local ok, value = pcall(json.decode, text)
    if ok and type(value) == "table" then return value end
    return nil
end

local function battle_time()
    local ok, value = pcall(function() return bm.battle:time_elapsed_ms() end)
    return ok and value or 0
end

local function log(text)
    local file = io.open(BRIDGE .. "mod.log", "a")
    if file then
        file:write(string.format("[%d] %s\n", battle_time(), tostring(text)))
        file:close()
    end
end

local function publish(name, value)
    local ok, text = pcall(json.encode, value)
    if not ok then log("encode failed: " .. tostring(text)); return false end
    local target, temporary = BRIDGE .. name, BRIDGE .. name .. ".tmp"
    local file = io.open(temporary, "w")
    if not file then log("cannot write " .. temporary); return false end
    file:write(text)
    file:close()
    os.remove(target)
    local renamed, err = os.rename(temporary, target)
    if not renamed then log("rename failed: " .. tostring(err)); return false end
    return true
end

local function clean_error(err)
    err = tostring(err)
    return string.match(err, ":%d+: (.*)$") or err
end

local function guarded(name, fn)
    return function(...)
        local ok, err = pcall(fn, ...)
        if not ok then log(name .. " failed: " .. clean_error(err)) end
    end
end

-- Engine queries, each isolated: a missing or failing method yields `default`.
local function get(object, method, default, ...)
    local ok, value = pcall(function(...) return object[method](object, ...) end, ...)
    if ok and value ~= nil then return value end
    return default
end

-- Ability state has no script getter; the UI's context system has it. One expression per
-- unit returns "key|field|...;key|..." rows (concatenation converts numbers and booleans).
local ABILITY_SETUP = 'BattleAbilityList.JoinString(SetupAbilityContext.RecordKey + "|" + '
    .. 'SetupAbilityContext.TargetType + "|" + SetupAbilityContext.ManaUsed + "|" + '
    .. 'SetupAbilityContext.RechargeTime, ";")'
local ABILITY_STATE = 'BattleAbilityList.JoinString(SetupAbilityContext.RecordKey + "|" + '
    .. 'CanCurrentlyPerform + "|" + RechargeTimeRemainingSecs + "|" + RemainingUses + "|" + '
    .. 'IsActive, ";")'
local ARMY_SETUP = 'PlayerArmyContext.ArmyAbilitiesList(false).JoinString(RecordKey + "|" + '
    .. 'TargetType + "|" + EffectRange + "|" + RechargeTime, ";")'

local function context_rows(context, id, expression)
    local ok, text = pcall(function() return common.get_context_value(context, id, expression) end)
    local rows = {}
    if not ok or type(text) ~= "string" then return rows end
    for item in string.gmatch(text, "[^;]+") do
        local fields = {}
        for field in string.gmatch(item .. "|", "([^|]*)|") do fields[#fields + 1] = field end
        rows[#rows + 1] = fields
    end
    return rows
end

-- "[[col:green]]Ground, Ally[[/col]]" -> "Ground, Ally"
local function plain(text)
    return (string.gsub(text or "", "%[%[.-%]%]", ""))
end

local function get_context(expression)
    local ok, value = pcall(function() return common.get_context_value("CcoBattleRoot", "", expression) end)
    if ok then return value end
    return nil
end

local function round(value, digits)
    if type(value) ~= "number" or value ~= value or value == (1 / 0) or value == -(1 / 0) then
        return nil
    end
    local scale = 10 ^ (digits or 0)
    return math.floor(value * scale + 0.5) / scale
end

-- From the land_units class (inf_mel, inf_mis, cav_shk, cav_mis, art_fld, mon, com, ...);
-- the is_* flags missed missile cavalry and war machines.
local CLASSES = {
    inf = "infantry", cav = "cavalry", chariot = "chariot", art = "artillery",
    mon = "monster", elph = "monster", com = "hero",
}

local function unit_class(unit)
    if get(unit, "is_commanding_unit", false) then return "lord" end
    local land_class = tostring(get(unit, "unit_class", ""))
    local class = CLASSES[string.match(land_class, "^(%a+)") or ""]
    if (not class or class == "monster") and get(unit, "can_fly", false) then return "flying" end
    if not class then return land_class ~= "" and land_class or "monster" end
    if (get(unit, "missile_range", 0) or 0) > 0 then
        if class == "infantry" then return "missile" end
        if class == "cavalry" or class == "chariot" then return "missile_" .. class end
    end
    return class
end

local function unit_record(id, unit, mine, class)
    local position = get(unit, "position", nil)
    local record = {
        id = id, type = get(unit, "type", "?"), class = class,
        commander = get(unit, "is_commanding_unit", false),
        x = position and round(position:get_x(), 1), z = position and round(position:get_z(), 1),
        bearing = round(get(unit, "bearing", 0)),
        men = get(unit, "number_of_men_alive", 0), men0 = get(unit, "initial_number_of_men", 0),
        hp = round(get(unit, "unary_hitpoints", 0), 2), state = {},
    }
    local flags = {
        {"is_routing", "routing"}, {"is_shattered", "shattered"}, {"is_wavering", "wavering"},
        {"is_in_melee", "melee"}, {"is_under_missile_attack", "under_fire"},
        {"is_moving", "moving"}, {"is_idle", "idle"},
        {"is_hidden", "hidden"}, {"is_unstable", "unstable"}, {"is_crumbling", "crumbling"},
        {"is_rampaging", "rampaging"},
    }
    for _, flag in ipairs(flags) do
        if get(unit, flag[1], false) then record.state[#record.state + 1] = flag[2] end
    end
    -- is_moving_fast follows the run setting, also while the unit stands.
    if get(unit, "is_moving", false) and get(unit, "is_moving_fast", false) then
        record.state[#record.state + 1] = "running"
    end
    record.range = round(get(unit, "missile_range", 0))
    if mine then
        local entry = state.friendly[id]
        record.ammo = get(unit, "ammo_left", 0)
        record.ammo0 = get(unit, "starting_ammo", 0)
        record.speed = {round(get(unit, "slow_speed", 0), 1), round(get(unit, "fast_speed", 0), 1)}
        record.fatigue = string.gsub(tostring(get(unit, "fatigue_state", "")), "^threshold_", "")
        record.width = round(get(unit, "ordered_width", 0), 1)
        record.attack_mode = entry.attack_mode
        record.command_queue = entry.command_queue
        record.behaviours = {}
        for _, key in ipairs(BEHAVIOURS) do
            if get(unit, "can_use_behaviour", false, key) then
                record.behaviours[key] = get(unit, "is_behaviour_active", false, key)
            end
        end
        record.abilities = {}
        local owned, live = get(unit, "owned_non_passive_special_abilities", {}), {}
        if #owned > 0 then
            for _, row in ipairs(context_rows("CcoBattleUnit", entry.ui_id, ABILITY_STATE)) do
                live[row[1]] = row
            end
        end
        for _, key in ipairs(owned) do
            local row, setup = live[key], entry.setup[key] or {}
            local recharge, uses = row and tonumber(row[3]), row and tonumber(row[4])
            record.abilities[#record.abilities + 1] = {
                key = key, can_use = get(unit, "can_perform_special_ability", false, key),
                ready = row and row[2] == "true", active = row and row[5] == "true",
                recharge_s = recharge and recharge > 0 and round(recharge, 1) or nil,
                uses = uses and uses >= 0 and uses or nil,
                target = setup.target, mana = setup.mana, cooldown_s = setup.cooldown_s,
                last_issued_ms = entry.ability_issued and entry.ability_issued[key],
            }
        end
        local target = get(unit, "current_target", nil)
        if target then record.target = state.enemy_by_ui[get(target, "unique_ui_id", -1)] end
        -- ordered_position is the unit's own position while it attacks.
        local destination = get(unit, "ordered_position", nil)
        if destination and entry.order == "move" and not record.target and get(unit, "is_moving", false) then
            record.dest = {round(destination:get_x(), 1), round(destination:get_z(), 1)}
        end
    end
    return record
end

-- Line of sight (is_visible_to_alliance) and concealment in grass or trees (is_hidden) are
-- separate tests; an enemy is shown only when it passes both.
local function visible_to_player(unit)
    if get(unit, "is_hidden", false) then return false end
    local ok, visible = pcall(function() return unit:is_visible_to_alliance(state.alliance) end)
    return ok and visible == true
end

-- Army abilities (Khorne's kill unlocks): the setup and unlocks from the context system
-- (indexes follow the list, which is ordered by cost), readiness from each ability's
-- button in the battle HUD: "inactive" or a cooldown timer means not ready.
local function army_abilities()
    local abilities = {}
    for _, setup in ipairs(state.army_abilities) do
        local record = {key = setup.key, target = setup.target, radius = setup.radius,
                        cooldown_s = setup.cooldown_s, cost = setup.cost,
                        last_issued_ms = state.army_issued[setup.key]}
        if setup.cost then
            record.unlocked = get_context("PlayerArmyContext.IsArmyAbilityUnlocked(" .. setup.index .. ")")
        end
        local button = ui.find({"army_ability_parent", "button_ability_" .. setup.key})
        if button then
            local timer = find_uicomponent(button, "dy_time_remaining")
            record.button = button:CurrentState()
            record.timer = timer and timer:Visible() and timer:GetStateText() or nil
            record.ready = record.button ~= "inactive" and record.timer == nil
        end
        abilities[#abilities + 1] = record
    end
    return {
        currency = get_context("PlayerArmyContext.ArmyAbilityCurrency"),
        next_unlock = get_context("PlayerArmyContext.CurrentArmyAbilityThreshold"),
        abilities = abilities,
    }
end

-- Objectives of the battle type, from the context system: capture points (alliance ids
-- there are 0-based, -1 for none; the script's are 1-based), tickets per alliance and the
-- army's supplies, for types that have them.
local CAPTURE_POINTS = 'CapturePointList.JoinString(Key + "|" + DisplayName + "|" + Position.x + "|" + '
    .. 'Position.z + "|" + CurrentHolderAlliance + "|" + IsContested + "|" + IsLocked + "|" + '
    .. 'CapturePercent + "|" + ContributesToVictory, ";")'
local TICKETS = 'AllianceList.JoinString(Id + "|" + TicketsRemaining + "|" + TicketsIncomePerSecond + "|" + '
    .. 'CpKillScore, ";")'

local function side(alliance_id)
    if alliance_id < 0 then return nil end
    if alliance_id == (state.info.player_alliance or bm:local_alliance() - 1) then return "us" end
    return state.info.alliances > 2 and ("alliance " .. (alliance_id + 1)) or "enemy"
end

local function mode_section()
    local section = {}
    for key, value in pairs(state.info) do section[key] = value end
    section.alliances, section.player_alliance = nil, nil
    local points = {}
    for _, row in ipairs(context_rows("CcoBattleRoot", "", CAPTURE_POINTS)) do
        points[#points + 1] = {
            id = row[1], name = row[2], x = round(tonumber(row[3]), 1), z = round(tonumber(row[4]), 1),
            holder = side(tonumber(row[5]) or -1), contested = row[6] == "true",
            locked = row[7] == "true", percent = round((tonumber(row[8]) or 0) * 100),
            victory = row[9] == "true",
        }
    end
    if #points > 0 then section.capture_points = points end
    -- Tickets count up: an alliance earns them each second for the points it holds (and
    -- for kills), and reaching the goal wins.
    local goal = tonumber(get_context("CaptureLocationManagerContext.TicketsGoal")) or 0
    local tickets = {}
    for _, row in ipairs(context_rows("CcoBattleRoot", "", TICKETS)) do
        local owner = side(tonumber(row[1]) or -1)
        local count, income = tonumber(row[2]) or 0, tonumber(row[3]) or 0
        if owner and (goal > 0 or count > 0) then
            tickets[#tickets + 1] = {side = owner, tickets = count, per_s = income, score = tonumber(row[4])}
        end
    end
    if #tickets > 0 then section.tickets, section.tickets_goal = tickets, goal end
    if get_context("HasSupplies") == true then
        section.supplies = tonumber(get_context("PlayerArmyContext.GlobalCurrency"))
    end
    return section
end

local function observation(now)
    state.seq = state.seq + 1
    local friendly, enemy, roster = {}, {}, {}
    for _, id in ipairs(state.friendly_ids) do
        local entry = state.friendly[id]
        local ok, record = pcall(unit_record, id, entry.unit, true, entry.class)
        friendly[#friendly + 1] = ok and record or {id = id, error = clean_error(record)}
    end
    for _, id in ipairs(state.enemy_ids) do
        local entry = state.enemy[id]
        local alive = get(entry.unit, "number_of_men_alive", 0) > 0
        -- A unit's destruction is reported only once the player has seen the unit.
        roster[#roster + 1] = {id = id, type = get(entry.unit, "type", "?"),
                               dead = (entry.seen and not alive) or nil,
                               alliance = state.info.alliances > 2 and entry.alliance or nil}
        if alive and visible_to_player(entry.unit) then
            entry.seen = true
            local ok, record = pcall(unit_record, id, entry.unit, false, entry.class)
            if ok and state.info.alliances > 2 then record.alliance = entry.alliance end
            enemy[#enemy + 1] = ok and record or {id = id, error = clean_error(record)}
        end
    end
    local army = nil
    if #state.army_abilities > 0 then
        local ok, value = pcall(army_abilities)
        army = ok and value or {error = clean_error(value)}
    end
    local remaining = get(bm.battle, "remaining_conflict_time", -1)
    local player = bm:get_player_army()
    local ok, section = pcall(mode_section)
    if not ok then section = {error = clean_error(section)} end
    return {
        schema = 1, job = session.job, battle = state.battle, seq = state.seq,
        phase = bm:get_current_phase_name(), time_ms = now, speed = 1,
        awaiting_orders = false, remaining_ms = remaining >= 0 and remaining * 1000 or -1,
        armies = {
            player = {faction = get(bm:get_player_army(), "faction_key", "?")},
            enemy = {faction = get(bm:get_first_non_player_army(), "faction_key", "?")},
        },
        friendly = friendly, enemy_roster = roster, enemy = enemy,
        magic = {
            current = get(player, "winds_of_magic_current", nil),
            reserve = get(player, "winds_of_magic_reserve", nil),
        },
        army = army, mode = section,
        orders = state.applied, result = state.result, final = state.final,
    }
end

local function publish_observation(now)
    local ok, message = pcall(observation, now)
    if not ok then log("observation failed: " .. clean_error(message)); return false end
    return publish("observation.json", message)
end

local function vector(x, y, z)
    if type(v) == "function" then return v(x, y, z) end
    return battle_vector:new(x, y, z)
end

local function apply_army_ability(order)
    local known = false
    for _, setup in ipairs(state.army_abilities) do
        if setup.key == order.ability then known = true end
    end
    if not known then error("unavailable_ability") end
    local x, z = tonumber(order.x), tonumber(order.z)
    if order.target ~= nil then
        if order.x ~= nil then error("ambiguous_ability_target") end
        local target = state.friendly[order.target] or state.enemy[order.target]
        if not target then error("unknown_target") end
        if get(target.unit, "number_of_men_alive", 0) <= 0 then error("target_dead") end
        if state.enemy[order.target] and not visible_to_player(target.unit) then
            error("target_not_visible")
        end
        local position = get(target.unit, "position", nil)
        x, z = position and position:get_x(), position and position:get_z()
    end
    if not x or not z then error("bad_position") end
    local y = get(bm.battle, "get_terrain_height", 0, x, z)
    bm:get_player_army():use_special_ability(order.ability, vector(x, y, z),
                                             tonumber(order.facing) or 0, tonumber(order.width) or 0)
    state.army_issued[order.ability] = battle_time()
end

local function apply_order(order)
    if order.unit == "army" and order.type == "ability" then
        if not state.started then return {unit = order.unit, ok = false, error = "deployment"} end
        local ok, err = pcall(apply_army_ability, order)
        return {unit = order.unit, ok = ok, error = not ok and clean_error(err) or nil}
    end
    local entry = state.friendly[order.unit]
    if not entry then return {unit = order.unit, ok = false, error = "unknown_unit"} end
    if not state.started then return {unit = order.unit, ok = false, error = "deployment"} end
    local unit, controller = entry.unit, entry.controller
    local ok, err = pcall(function()
        if get(unit, "number_of_men_alive", 0) == 0 then error("unit_dead") end
        if get(unit, "is_routing", false) or get(unit, "is_shattered", false) then
            error("unit_routing")
        end
        if order.type == "move" then
            local x, z = tonumber(order.x), tonumber(order.z)
            if not x or not z then error("bad_position") end
            local y = get(bm.battle, "get_terrain_height", 0, x, z)
            local destination = vector(x, y, z)
            if not get(unit, "can_reach_position", true, destination) then error("unreachable") end
            local facing, width = tonumber(order.facing), tonumber(order.width)
            if width and width <= 0 then error("bad_width") end
            if facing or width then
                facing = facing or get(unit, "bearing", 0)
                width = width or get(unit, "ordered_width", 0)
                local method = order.queue and "goto_location_angle_width_q" or "goto_location_angle_width"
                controller[method](controller, destination, facing,
                                   width > 0 and width or 40, order.run == true)
            else
                local method = order.queue and "goto_location_q" or "goto_location"
                controller[method](controller, destination, order.run == true)
            end
        elseif order.type == "attack" then
            local target = state.enemy[order.target]
            if not target then error("unknown_target") end
            if get(target.unit, "number_of_men_alive", 0) == 0 then error("target_dead") end
            if not visible_to_player(target.unit) then error("target_not_visible") end
            local mode = order.mode or "auto"
            if mode ~= "auto" and mode ~= "melee" and mode ~= "ranged" then error("bad_attack_mode") end
            if mode == "ranged" and get(unit, "ammo_left", 0) <= 0 then error("no_ammunition") end
            -- Queued attacks select the attack method without changing the current move.
            if not order.queue then controller:melee(mode == "melee") end
            local method = order.queue and "attack_unit_q" or "attack_unit"
            local primary = mode ~= "melee" or get(unit, "missile_range", 0) == 0
            controller[method](controller, target.unit, primary, order.run == true)
            entry.attack_mode = mode
        elseif order.type == "halt" then
            controller:halt()
        elseif order.type == "behaviour" then
            local allowed = false
            for _, key in ipairs(BEHAVIOURS) do if key == order.behaviour then allowed = true end end
            if not allowed or not get(unit, "can_use_behaviour", false, order.behaviour) then
                error("unavailable_behaviour")
            end
            if type(order.enabled) ~= "boolean" then error("bad_enabled") end
            controller:change_behaviour_active(order.behaviour, order.enabled)
        elseif order.type == "ability" then
            local owned = false
            for _, key in ipairs(get(unit, "owned_non_passive_special_abilities", {})) do
                if key == order.ability then owned = true end
            end
            if not owned or not get(unit, "can_perform_special_ability", false, order.ability) then
                error("unavailable_ability")
            end
            if order.x ~= nil then
                if order.target ~= nil then error("ambiguous_ability_target") end
                local x, z = tonumber(order.x), tonumber(order.z)
                if not x or not z then error("bad_position") end
                local y = get(bm.battle, "get_terrain_height", 0, x, z)
                controller:perform_special_ability_ground(order.ability, vector(x, y, z),
                                                         tonumber(order.facing) or 0, tonumber(order.width) or 0)
            elseif order.target then
                local target = state.friendly[order.target] or state.enemy[order.target]
                if not target then error("unknown_target") end
                if get(target.unit, "number_of_men_alive", 0) <= 0 then error("target_dead") end
                if state.enemy[order.target] and not visible_to_player(target.unit) then
                    error("target_not_visible")
                end
                controller:perform_special_ability(order.ability, target.unit)
            else
                -- This build requires a unit argument even for an ability cast on self.
                controller:perform_special_ability(order.ability, unit)
            end
            entry.ability_issued = entry.ability_issued or {}
            entry.ability_issued[order.ability] = battle_time()
        else
            error("unknown_type")
        end
    end)
    if ok then
        if order.type == "move" or order.type == "attack" or order.type == "halt" then
            if order.queue then
                entry.command_queue = entry.command_queue or {entry.command}
                entry.command_queue[#entry.command_queue + 1] = order
            else
                entry.order, entry.command, entry.command_queue = order.type, order, nil
            end
        end
        return {unit = order.unit, ok = true, queued = order.queue == true}
    end
    return {unit = order.unit, ok = false, error = clean_error(err)}
end

local function apply_pending(now)
    local message = state.pending
    state.pending = nil
    if type(message.say) == "string" then
        local shown, err = pcall(function() common.advice(message.say) end)
        if not shown then log("advice failed: " .. clean_error(err)) end
    end
    local results, failed, previous = {}, {}, {}
    for index, order in ipairs(message.orders or {}) do
        local result
        if order.queue and (failed[order.unit] or previous[order.unit] ~= "move"
                            or (order.type ~= "move" and order.type ~= "attack")) then
            result = {unit = order.unit, ok = false, error = "queue_predecessor_failed_or_missing"}
        else
            result = apply_order(order)
        end
        result.index = index
        results[#results + 1] = result
        if order.type == "move" or order.type == "attack" or order.type == "halt" then
            previous[order.unit] = order.type
            failed[order.unit] = not result.ok
        end
    end
    state.applied = {
        request = message.request, based_on = message.based_on, applied_ms = now, results = results,
    }
    state.applied_ms = now
    state.force_observe = true
    log(string.format("applied %s (%d orders)", tostring(message.request), #results))
end

local function try_end_deployment()
    local ok, err = pcall(function() bm.battle:end_current_battle_phase() end)
    log("end_current_battle_phase: " .. (ok and "ok" or clean_error(err)))
    if ok then return end
    local clicked, err2 = pcall(function()
        local button = find_uicomponent(core:get_ui_root(), "button_battle_start")
        if not button then error("button_battle_start not found") end
        button:SimulateLClick()
    end)
    log("start button click: " .. (clicked and "ok" or clean_error(err2)))
end

-- True strength of one side, alive and at the start, over every unit seen or not.
local function strength(entries)
    local men, men0 = 0, 0
    for _, entry in pairs(entries) do
        men = men + get(entry.unit, "number_of_men_alive", 0)
        men0 = men0 + get(entry.unit, "initial_number_of_men", 0)
    end
    return {men = men, men0 = men0}
end

local function finish()
    if state.finished then return end
    local battle = bm.battle
    if not get(battle, "battle_outcome_decided", false) then return end
    local winner, mine = get(battle, "victorious_alliance", 0), get(battle, "local_alliance", 1)
    if winner == -1 or get(battle, "is_draw", false) then
        state.result = "draw"
    elseif winner == 0 then
        return
    else
        state.result = winner == mine and "won" or "lost"
    end
    state.finished = true
    -- For evaluation only: the result observation ends the episode before any decision.
    state.final = {friendly = strength(state.friendly), enemy = strength(state.enemy)}
    for _, entry in pairs(state.friendly) do
        pcall(function() entry.controller:release_control() end)
    end
    publish_observation(battle_time())
    bm:remove_process("twwarhammer3_tick")
    log("result " .. state.result)
end

-- The results popup's rematch button, then the "Are you sure?" dialog's tick, reload the
-- same battle (bm:restart_battle(), the RestartBattle context command, did nothing on the
-- results screen). A decided battle is ended at once so the popup opens; RestartBattle is
-- the fallback before a decision.
local function restart()
    if state.finished then pcall(function() bm:end_battle() end) end
    local waited, rematched = 0, false
    bm:repeat_real_callback(guarded("restart", function()
        waited = waited + 1000
        local button = ui.find(rematched and CONFIRM or REMATCH)
        if button and not rematched then
            button:SetVisible(true)
            button:SimulateLClick()
            rematched = true
            log("rematch clicked")
        elseif button then
            bm:remove_real_callback("twwarhammer3_restart")
            button:SimulateLClick()
            log("rematch confirmed")
        elseif waited >= (state.finished and 60000 or 3000) then
            bm:remove_real_callback("twwarhammer3_restart")
            log(rematched and "no rematch confirmation" or "no rematch button")
            if not state.finished then bm:restart_battle() end
        end
    end), 1000, "twwarhammer3_restart")
end

-- Registers units not seen before: every unit at the start, then reinforcements, survival
-- waves and purchased units as they enter the field. Friendly units get a controller each;
-- enemies come from every other alliance (several in a free-for-all).
local function scan()
    local army = bm:get_player_army()
    local units = army:units()
    for index = 1, units:count() do
        local unit = units:item(index)
        local key = get(unit, "unique_ui_id", nil)
        if key and not state.known[key] then
            state.known[key] = true
            local id = "f" .. (#state.friendly_ids + 1)
            local controller = army:create_unit_controller()
            controller:add_units(unit)
            controller:take_control()
            local entry = {unit = unit, controller = controller, class = unit_class(unit),
                           ui_id = tostring(key), setup = {}}
            for _, row in ipairs(context_rows("CcoBattleUnit", entry.ui_id, ABILITY_SETUP)) do
                entry.setup[row[1]] = {target = plain(row[2]), mana = tonumber(row[3]),
                                       cooldown_s = tonumber(row[4])}
            end
            state.friendly[id] = entry
            state.friendly_ids[#state.friendly_ids + 1] = id
            if state.started_ms then log("new friendly unit " .. id .. " " .. get(unit, "type", "?")) end
        end
    end
    local alliances = bm:alliances()
    for alliance = 1, alliances:count() do
        local armies = alliance ~= bm:local_alliance() and alliances:item(alliance):armies()
        for army_index = 1, armies and armies:count() or 0 do
            local enemy_units = armies:item(army_index):units()
            for index = 1, enemy_units:count() do
                local unit = enemy_units:item(index)
                local key = get(unit, "unique_ui_id", nil)
                if key and not state.known[key] then
                    state.known[key] = true
                    local id = "e" .. (#state.enemy_ids + 1)
                    state.enemy[id] = {unit = unit, class = unit_class(unit), alliance = alliance}
                    state.enemy_ids[#state.enemy_ids + 1] = id
                    state.enemy_by_ui[key] = id
                    if state.started_ms then log("new enemy unit " .. id .. " " .. get(unit, "type", "?")) end
                end
            end
        end
    end
end

-- What the battle type is and asks for, read once: the player's role, who wins when time
-- runs out, and the objectives as the game's battle-type cheat sheet states them.
local function battle_info()
    local info = {alliances = bm:alliances():count(), type = get_context("BattleTypeState"),
                  player_alliance = tonumber(get_context("PlayerAllianceContext.Id"))}
    state.info.player_alliance = info.player_alliance
    local attacker = get_context("SetupContext.IsPlayerAttacker")
    if type(attacker) == "boolean" then info.role = attacker and "attacker" or "defender" end
    local timeout = get_context("TimeoutWinningAllianceIndex")
    if type(timeout) == "number" then info.timeout_winner = side(timeout) or "none" end
    local objectives = get_context('BattleTypeCheatSheetList(0).JoinString(HeaderText + ": " + '
                                   .. 'DescriptionText, " ")')
    if type(objectives) == "string" and objectives ~= "" then info.objectives = objectives end
    return info
end

local function tick()
    local now = battle_time()
    if state.pending then apply_pending(now) end
    if not state.finished and get(bm.battle, "battle_outcome_decided", false) then
        finish()
        return
    end
    if state.force_observe or now >= state.next_observe_ms then
        if now >= state.next_observe_ms then
            local ok, err = pcall(scan)
            if not ok then log("scan failed: " .. clean_error(err)) end
        end
        state.force_observe = false
        state.next_observe_ms = now + (session.observe_ms or 1000)
        publish_observation(now)
    end
end

-- UI steps for probing the battle UI (menu --battle): the frontend script is unloaded
-- during a battle, so menu.json is free, and orders.json stays the job's alone.
local function run_menu()
    local text = read_file(BRIDGE .. "menu.json")
    if not text then return end
    os.remove(BRIDGE .. "menu.json")
    local ok, message = pcall(json.decode, text)
    if not ok or type(message) ~= "table" or type(message.steps) ~= "table" then return end
    for index, step in ipairs(message.steps) do
        local done_ok, done = pcall(ui.run, step, BRIDGE)
        log(string.format("ui %d: %s", index, done_ok and tostring(done) or clean_error(done)))
    end
end

local function poll()
    run_menu()
    local text = read_file(BRIDGE .. "orders.json")
    if not text then return end
    os.remove(BRIDGE .. "orders.json")
    local ok, message = pcall(json.decode, text)
    if not ok or type(message) ~= "table" then log("orders.json unreadable; dropped"); return end
    if message.job ~= session.job or message.battle ~= state.battle then
        log("stale request " .. tostring(message.request) .. " for battle " .. tostring(message.battle))
        return
    end
    if message.request == state.last_request then
        log("duplicate request " .. tostring(message.request))
        return
    end
    state.last_request = message.request
    if message.control == "restart" then
        log("restart requested by " .. tostring(message.request))
        restart()
        return
    elseif message.control == "start" then
        try_end_deployment()
        return
    elseif message.control then
        log("unknown control " .. tostring(message.control))
        return
    end
    state.pending = message
end

local function start()
    if state.started then return end
    state.started = true
    state.alliance = bm:get_player_alliance()
    state.info = {alliances = bm:alliances():count()}
    local ok, info = pcall(battle_info)
    if ok then state.info = info else log("battle info failed: " .. clean_error(info)) end
    scan()
    state.started_ms = battle_time()
    local fill = get_context("HasArmyAbilityFillCurrency") == true
    for index, row in ipairs(context_rows("CcoBattleRoot", "", ARMY_SETUP)) do
        state.army_abilities[index] = {
            key = row[1], target = plain(row[2]), radius = tonumber(row[3]),
            cooldown_s = tonumber(row[4]), index = index - 1,
            cost = fill and get_context("PlayerArmyContext.ArmyAbilityIndexCost(" .. (index - 1) .. ")") or nil,
        }
    end
    bm:modify_battle_speed(1, true)
    state.force_observe = true
    bm:repeat_callback(tick, session.tick_ms or 250, "twwarhammer3_tick")
    log(string.format("started: %s, %d alliances, %d friendly, %d enemy units", tostring(state.info.type),
                      state.info.alliances, #state.friendly_ids, #state.enemy_ids))
end

local function load()
    session = read_json(BRIDGE .. "session.json")
    if not session or session.enabled == false then return end
    local battle = bm.battle
    for _, check in ipairs({"is_multiplayer", "is_replay", "is_from_campaign", "is_quest_battle", "is_tutorial"}) do
        if get(battle, check, false) then
            log("inactive: " .. check)
            return
        end
    end
    state.battle = string.format("%d-%s", os.time(), tostring(os.clock()))
    log("loaded battle " .. state.battle .. " for job " .. tostring(session.job))
    bm:register_phase_change_callback("Deployed", guarded("start", start))
    bm:register_phase_change_callback("VictoryCountdown", guarded("finish", finish))
    bm:register_phase_change_callback("Complete", guarded("finish", finish))
    bm:repeat_real_callback(guarded("poll", poll), 200, "twwarhammer3_poll")
    if session.autostart then
        -- Deployment begins after the loading screen; keep trying until combat starts.
        bm:repeat_real_callback(guarded("autostart", function()
            if state.started or state.finished then
                bm:remove_real_callback("twwarhammer3_autostart")
            elseif bm:get_current_phase_name() == "Deployment" then
                try_end_deployment()
            end
        end), 5000, "twwarhammer3_autostart")
    end
    publish("observation.json", {
        schema = 1, job = session.job, battle = state.battle, seq = 0, phase = "Loading",
        time_ms = 0, speed = 1, awaiting_orders = false, friendly = {},
        enemy_roster = {}, enemy = {},
    })
end

local ok, err = pcall(load)
if not ok then log("load failed: " .. clean_error(err)) end
