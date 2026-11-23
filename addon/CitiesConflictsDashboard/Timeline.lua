local ADDON_NAME, LifeDashboard = ...
LifeDashboard = LifeDashboard or {}
_G["CitiesConflictsDashboard"] = LifeDashboard
_G["PlayerbotsLifeDashboard"] = LifeDashboard

local Timeline = {}
LifeDashboard.Timeline = Timeline

function Timeline:GetBotTimeline(guid)
    local bot = LifeDashboard.Store and LifeDashboard.Store.bots and LifeDashboard.Store.bots[guid]
    if not bot then return {} end

    local entries = {}
    local isAuthoritative = (bot.truthSource == "server-authoritative")
    local isDemo = (bot.truthSource == "demo")

    -- 1. Last Action / Observed Execution
    if bot.lastAction and bot.lastAction ~= "" then
        local actionSource
        local truth
        if isAuthoritative then
            actionSource = "Server Telemetry Bridge"
            truth = "OBSERVED"
        elseif isDemo then
            actionSource = "Demo Telemetry"
            truth = "ESTIMATED"
        else
            actionSource = "Client Unit Observation"
            truth = "OBSERVED"
        end

        table.insert(entries, {
            truthClass = truth,
            title = "Action: " .. bot.lastAction,
            seenAt = bot.actionHistory and bot.actionHistory[1] and bot.actionHistory[1].seenAt,
            dueMs = 0,
            source = actionSource,
            icon = "Interface\\Icons\\Spell_Holy_BlessingOfStrength",
        })
    end

    -- 2. Current Activity State
    if bot.activity and bot.activity ~= "" then
        local actTitle = (LifeDashboard.L and LifeDashboard.L["ACT_" .. bot.activity]) or bot.activity
        local modSource
        if isAuthoritative then
            modSource = (bot.module == "city" and "Living Cities Server Bridge" or "World Conflicts Server Bridge")
        elseif isDemo then
            modSource = (bot.module == "city" and "Living Cities (Mock)" or "World Conflicts (Mock)")
        else
            modSource = "Client World Observation"
        end

        table.insert(entries, {
            truthClass = isAuthoritative and "OBSERVED" or (isDemo and "ESTIMATED" or "OBSERVED"),
            title = "Activity: " .. actTitle,
            dueMs = 0,
            source = modSource,
            icon = "Interface\\Icons\\Achievement_Zone_Stormwind",
        })
    end

    -- 3. Next Task
    if bot.nextTask and bot.nextTask ~= "" then
        local taskTruth = string.upper(bot.truthClass or (isAuthoritative and "QUEUED" or "ESTIMATED"))
        table.insert(entries, {
            truthClass = taskTruth,
            title = "Next Task: " .. bot.nextTask,
            dueMs = bot.dueMs or 0,
            source = isAuthoritative and "Server Task Scheduler" or (isDemo and "Mock Scheduler" or "Local Discretion"),
            icon = "Interface\\Icons\\Spell_ChargePositive",
        })
    end

    -- 4. Server Work Queue Matches
    if LifeDashboard.Store and LifeDashboard.Store.workQueues then
        for _, item in ipairs(LifeDashboard.Store.workQueues) do
            if item.botGuid == guid or item.botName == bot.name then
                table.insert(entries, {
                    truthClass = string.upper(item.truthClass or "QUEUED"),
                    title = string.upper(item.queue) .. ": " .. item.taskType,
                    dueMs = item.dueMs or 0,
                    source = isAuthoritative and "Authoritative Server Queue" or "Demo Queue",
                    icon = "Interface\\Icons\\Ability_Hunter_MasterMarksman",
                })
            end
        end
    end

    if isAuthoritative and bot.actionHistory then
        for i = 2, math.min(4, #bot.actionHistory) do
            local sample = bot.actionHistory[i]
            table.insert(entries, {
                truthClass = "OBSERVED",
                title = "Earlier: " .. sample.action,
                seenAt = sample.seenAt,
                source = sample.module == "city" and "Living Cities" or "World Conflicts",
            })
        end
    end

    return entries
end
