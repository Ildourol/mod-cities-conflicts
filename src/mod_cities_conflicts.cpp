/*
 * Cities & Conflicts (mod-cities-conflicts)
 * Combined Urban Life & World Conflicts Module
 * Copyright (C) 2026 iCore
 * SPDX-License-Identifier: GPL-2.0-or-later
 */

#include "CityLifeMgr.h"
#include "CityLifeBeggarTrade.h"
#include "CityLifeCustomSocial.h"
#include "CityLifeHumanBehavior.h"
#include "PvPLifeMgr.h"
#include "LifeBotReservation.h"
#include "LifeTelemetryBridge.h"

#include "Chat.h"
#include "CommandScript.h"
#include "Group.h"
#include "GroupScript.h"
#include "ObjectAccessor.h"
#include "Player.h"
#include "PlayerScript.h"
#include "ScriptMgr.h"
#include "SharedDefines.h"
#include "WorldScript.h"

using namespace Acore::ChatCommands;

// ============================================================================
// City Life World Script
// ============================================================================
class CityLifeWorldScript : public WorldScript
{
public:
    CityLifeWorldScript()
        : WorldScript("CityLifeWorldScript", { WORLDHOOK_ON_AFTER_CONFIG_LOAD, WORLDHOOK_ON_UPDATE, WORLDHOOK_ON_SHUTDOWN })
    {
    }

    void OnAfterConfigLoad(bool /*reload*/) override
    {
        sCityLifeMgr.LoadConfig();
    }

    void OnUpdate(uint32 diff) override
    {
        sCityLifeMgr.Update(diff);
    }

    void OnShutdown() override
    {
        sCityLifeMgr.Shutdown();
        PlayerbotsLife::LifeTelemetryBridge::Instance().UnregisterProvider("city");
        PlayerbotsLife::UnregisterActiveModule(PlayerbotsLife::ModuleSystemFlags::MODULE_CITY_LIFE);
    }
};

// ============================================================================
// City Life Player Script
// ============================================================================
class CityLifePlayerScript : public PlayerScript
{
public:
    CityLifePlayerScript()
        : PlayerScript("CityLifePlayerScript", {
            PLAYERHOOK_ON_LOGIN,
            PLAYERHOOK_ON_LOGOUT,
            PLAYERHOOK_ON_UPDATE_ZONE,
            PLAYERHOOK_ON_TEXT_EMOTE,
            PLAYERHOOK_ON_PLAYER_ENTER_COMBAT,
            PLAYERHOOK_CAN_INIT_TRADE,
            PLAYERHOOK_CAN_SET_TRADE_ITEM,
            PLAYERHOOK_ON_BEFORE_ACHI_COMPLETE,
            PLAYERHOOK_ON_BEFORE_CRITERIA_PROGRESS
        })
    {
    }

    void OnPlayerLogin(Player* player) override
    {
        sCityLifeMgr.OnPlayerLogin(player);
    }

    void OnPlayerLogout(Player* player) override
    {
        sCityLifeMgr.OnPlayerLogout(player);
    }

    void OnPlayerUpdateZone(Player* player, uint32 newZone, uint32 /*newArea*/) override
    {
        sCityLifeMgr.OnPlayerZoneUpdate(player, newZone);
    }

    void OnPlayerTextEmote(Player* player, uint32 textEmote, uint32 /*emoteNum*/, ObjectGuid guid) override
    {
        sCityLifeCustomSocial.OnTextEmote(player, textEmote, guid);
    }

    void OnPlayerEnterCombat(Player* player, Unit* /*enemy*/) override
    {
        sCityLifeHumanBehavior.Wake(player);
    }

    bool OnPlayerCanInitTrade(Player* player, Player* target) override
    {
        if (sCityLifeBeggarTrade.IsInitiating(player, target))
            return true;

        if (!sCityLifeMgr.IsInteractionsEnabled() || !sCityLifeMgr.IsPlayerTradingEnabled())
        {
            bool targetIsResident = target && sCityLifeMgr.IsResident(target->GetGUID().GetCounter());
            bool playerIsResident = player && sCityLifeMgr.IsResident(player->GetGUID().GetCounter());
            if (targetIsResident || playerIsResident)
            {
                if (targetIsResident)
                    target->Whisper("Trading is disabled.", LANG_UNIVERSAL, player);
                return false;
            }
        }
        return true;
    }

    bool OnPlayerCanSetTradeItem(Player* player, Item* /*tradedItem*/, uint8 tradeSlot) override
    {
        if (tradeSlot == TRADE_SLOT_NONTRADED)
            return true;

        uint32 const guidLow = player ? player->GetGUID().GetCounter() : 0;
        if (sCityLifeBeggarTrade.IsBeggar(guidLow))
            return false;

        if (!sCityLifeMgr.IsInteractionsEnabled() || !sCityLifeMgr.IsPlayerTradingEnabled())
        {
            if (player && sCityLifeMgr.IsResident(player->GetGUID().GetCounter()))
                return false;
        }
        return true;
    }

    bool OnPlayerBeforeAchievementComplete(Player* player, AchievementEntry const* /*achievement*/) override
    {
        if (!player || !sCityLifeMgr.IsBlockAchievementsEnabled())
            return true;

        if (::IsRealPlayer(player) || ::IsSelfBot(player))
            return true;

        uint32 const guidLow = player->GetGUID().GetCounter();
        if (sCityLifeMgr.IsResidentInSyntheticActivity(guidLow))
        {
            sCityLifeMgr.RecordSuppressedAchievement();
            return false;
        }

        return true;
    }

    bool OnPlayerBeforeCriteriaProgress(Player* player, AchievementCriteriaEntry const* /*criteria*/) override
    {
        if (!player || !sCityLifeMgr.IsBlockAchievementsEnabled())
            return true;

        if (::IsRealPlayer(player) || ::IsSelfBot(player))
            return true;

        uint32 const guidLow = player->GetGUID().GetCounter();
        if (sCityLifeMgr.IsResidentInSyntheticActivity(guidLow))
        {
            sCityLifeMgr.RecordSuppressedCriteria();
            return false;
        }

        return true;
    }
};

// ============================================================================
// City Life Group Script
// ============================================================================
class CityLifeGroupScript : public GroupScript
{
public:
    CityLifeGroupScript()
        : GroupScript("CityLifeGroupScript", { GROUPHOOK_ON_ADD_MEMBER })
    {
    }

    void OnAddMember(Group* group, ObjectGuid guid) override
    {
        if (!group)
            return;

        bool hasRealPlayer = false;
        for (GroupReference const* ref = group->GetFirstMember(); ref != nullptr; ref = ref->next())
        {
            Player const* member = ref->GetSource();
            if (member && member->GetSession() && !member->GetSession()->IsHeadless())
            {
                hasRealPlayer = true;
                break;
            }
        }

        if (hasRealPlayer)
        {
            sCityLifeMgr.DisengageResident(guid.GetCounter());
            for (GroupReference const* ref = group->GetFirstMember(); ref; ref = ref->next())
                if (Player* member = ref->GetSource(); member && sCityLifeMgr.IsResident(member->GetGUID().GetCounter()))
                    sCityLifeMgr.DisengageResident(member->GetGUID().GetCounter());
        }
    }
};

// ============================================================================
// City Life Command Script
// ============================================================================
class CityLifeCommandScript : public CommandScript
{
public:
    CityLifeCommandScript() : CommandScript("CityLifeCommandScript") { }

    ChatCommandTable GetCommands() const override
    {
        static ChatCommandTable commandTable =
        {
            { "citylife", HandleCityLifeCommand, SEC_GAMEMASTER, Console::Yes }
        };
        return commandTable;
    }

    static bool HandleCityLifeCommand(ChatHandler* handler, char const* args)
    {
        return sCityLifeMgr.HandleCommand(handler, args ? args : "");
    }
};

// ============================================================================
// City Life Telemetry Provider
// ============================================================================
class CityLifeTelemetryProvider : public PlayerbotsLife::ILifeTelemetryProvider
{
public:
    std::string GetModuleName() const override { return "city"; }

    void BuildCapacity(uint32& target, uint32& active, uint32& pending, uint32& releasing) override
    {
        target = sCityLifeMgr.GetTotalTargetPopulation();
        active = sCityLifeMgr.GetResidentCount();
        pending = sCityLifeMgr.GetPendingAdmissionCount();
        releasing = sCityLifeMgr.GetReleasingCount();
    }

    void BuildRoster(std::vector<std::string>& outRecords) override
    {
        sCityLifeMgr.BuildTelemetryRoster(outRecords);
    }

    void BuildHubsOrZones(std::string& outPayload) override
    {
        sCityLifeMgr.BuildTelemetryHubs(outPayload);
    }

    void BuildQueues(std::string& outPayload) override
    {
        sCityLifeMgr.BuildTelemetryQueues(outPayload);
    }

    uint32 GetLiveBotCensus() const override
    {
        return sCityLifeMgr.GetLiveBotCensus();
    }

    bool BuildBotDetail(uint32 guidLow, std::string& outPayload) override
    {
        return sCityLifeMgr.BuildBotDetail(guidLow, outPayload);
    }
};

// ============================================================================
// PvP Life World Script
// ============================================================================
class PvPLifeWorldScript : public WorldScript
{
public:
    PvPLifeWorldScript()
        : WorldScript("PvPLifeWorldScript", { WORLDHOOK_ON_AFTER_CONFIG_LOAD, WORLDHOOK_ON_UPDATE, WORLDHOOK_ON_SHUTDOWN })
    {
    }

    void OnAfterConfigLoad(bool /*reload*/) override
    {
        sPvPLifeMgr.LoadConfig();
    }

    void OnUpdate(uint32 diff) override
    {
        sPvPLifeMgr.Update(diff);
    }

    void OnShutdown() override
    {
        sPvPLifeMgr.Shutdown();
        PlayerbotsLife::LifeTelemetryBridge::Instance().UnregisterProvider("pvp");
        PlayerbotsLife::UnregisterActiveModule(PlayerbotsLife::MODULE_PVP_LIFE);
    }
};

// ============================================================================
// PvP Life Player Script
// ============================================================================
class PvPLifePlayerScript : public PlayerScript
{
public:
    PvPLifePlayerScript()
        : PlayerScript("PvPLifePlayerScript", { PLAYERHOOK_ON_LOGOUT })
    {
    }

    void OnPlayerLogout(Player* player) override
    {
        if (player)
            sPvPLifeMgr.OnPlayerLogout(player->GetGUID().GetCounter());
    }
};

// ============================================================================
// PvP Life Group Script
// ============================================================================
class PvPLifeGroupScript : public GroupScript
{
public:
    PvPLifeGroupScript()
        : GroupScript("PvPLifeGroupScript", { GROUPHOOK_ON_ADD_MEMBER })
    {
    }

    void OnAddMember(Group* group, ObjectGuid guid) override
    {
        if (!group)
            return;

        bool hasRealPlayer = false;
        for (GroupReference const* ref = group->GetFirstMember(); ref != nullptr; ref = ref->next())
        {
            Player const* member = ref->GetSource();
            if (member && member->GetSession() && !member->GetSession()->IsBot())
            {
                hasRealPlayer = true;
                break;
            }
        }

        if (hasRealPlayer)
        {
            sPvPLifeMgr.OnAddGroupMember(guid.GetCounter());
            for (GroupReference const* ref = group->GetFirstMember(); ref != nullptr; ref = ref->next())
            {
                Player const* member = ref->GetSource();
                if (member && member->GetSession() && member->GetSession()->IsBot())
                    sPvPLifeMgr.OnAddGroupMember(member->GetGUID().GetCounter());
            }
        }
    }
};

// ============================================================================
// PvP Life Command Script
// ============================================================================
class PvPLifeCommandScript : public CommandScript
{
public:
    PvPLifeCommandScript() : CommandScript("PvPLifeCommandScript") { }

    ChatCommandTable GetCommands() const override
    {
        static ChatCommandTable commandTable =
        {
            { "pvplife", HandlePvPLifeCommand, SEC_GAMEMASTER, Console::Yes },
            { "wpvp",    HandleWpvpCommand,    SEC_GAMEMASTER, Console::Yes }
        };
        return commandTable;
    }

    static bool HandlePvPLifeCommand(ChatHandler* handler, char const* args)
    {
        return sPvPLifeMgr.HandleCommand(handler, args ? args : "");
    }

    static bool HandleWpvpCommand(ChatHandler* handler, char const* args)
    {
        return sPvPLifeMgr.HandleWpvpCommand(handler, args ? args : "");
    }
};

// ============================================================================
// PvP Life Telemetry Provider
// ============================================================================
class PvPLifeTelemetryProvider : public PlayerbotsLife::ILifeTelemetryProvider
{
public:
    std::string GetModuleName() const override { return "pvp"; }

    void BuildCapacity(uint32& target, uint32& active, uint32& pending, uint32& releasing) override
    {
        target = sPvPLifeMgr.GetTargetPopulationBudget();
        active = sPvPLifeMgr.GetActiveParticipantCount();
        pending = sPvPLifeMgr.GetPendingCount();
        releasing = sPvPLifeMgr.GetReleasingCount();
    }

    void BuildRoster(std::vector<std::string>& outRecords) override
    {
        sPvPLifeMgr.BuildTelemetryRoster(outRecords);
    }

    void BuildHubsOrZones(std::string& outPayload) override
    {
        sPvPLifeMgr.BuildTelemetryZones(outPayload);
    }

    void BuildQueues(std::string& outPayload) override
    {
        sPvPLifeMgr.BuildTelemetryQueues(outPayload);
    }

    uint32 GetLiveBotCensus() const override
    {
        return sPvPLifeMgr.GetLiveBotCensus();
    }

    bool BuildBotDetail(uint32 guidLow, std::string& outPayload) override
    {
        return sPvPLifeMgr.BuildBotDetail(guidLow, outPayload);
    }
};

// ============================================================================
// Module Registration Entrypoint
// ============================================================================
void AddCitiesConflictsScripts()
{
    static_assert(PlayerbotsLife::LIFE_BOT_RESERVATION_PROTOCOL_VERSION == 2026101104,
        "Cities & Conflicts requires LifeBotReservation protocol version 2026101104");

    // Register active flags for both systems
    PlayerbotsLife::RegisterActiveModule(PlayerbotsLife::ModuleSystemFlags::MODULE_CITY_LIFE);
    PlayerbotsLife::RegisterActiveModule(PlayerbotsLife::ModuleSystemFlags::MODULE_PVP_LIFE);

    PlayerbotsLife::RegisterTelemetryBridge();
    PlayerbotsLife::LifeTelemetryBridge::Instance().RegisterProvider(std::make_shared<CityLifeTelemetryProvider>());
    PlayerbotsLife::LifeTelemetryBridge::Instance().RegisterProvider(std::make_shared<PvPLifeTelemetryProvider>());

    // Initialize City Life scripts
    new CityLifeWorldScript();
    new CityLifePlayerScript();
    new CityLifeGroupScript();
    new CityLifeCommandScript();

    // Initialize World Conflicts scripts
    new PvPLifeWorldScript();
    new PvPLifePlayerScript();
    new PvPLifeGroupScript();
    new PvPLifeCommandScript();

    LOG_INFO("server.loading", ">> Loaded mod-cities-conflicts (protocol={}, registry={:p})",
        PlayerbotsLife::GetReservationProtocolVersion(), PlayerbotsLife::GetReservationRegistryAddress());
}
