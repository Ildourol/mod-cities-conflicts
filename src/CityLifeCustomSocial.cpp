/*
 * Living Cities - Bidirectional Social & Emote Reaction Engine
 * Copyright (C) 2026 iCore
 * SPDX-License-Identifier: GPL-2.0-or-later
 */

#include "CityLifeCustomSocial.h"
#include "CityLifeMgr.h"

#include "Config.h"
#include "GameTime.h"
#include "Log.h"
#include "ObjectAccessor.h"
#include "Player.h"
#include "PlayerbotAI.h"
#include "Playerbots.h"
#include "Random.h"
#include "SharedDefines.h"

#include <algorithm>

namespace
{
    uint32 SocialTime()
    {
        return static_cast<uint32>(GameTime::GetGameTime().count());
    }

    Player* FindSocialPlayer(uint32 guid)
    {
        return ObjectAccessor::FindPlayer(ObjectGuid::Create<HighGuid::Player>(guid));
    }

    uint32 ReactionEmote(uint32 textEmote)
    {
        switch (textEmote)
        {
            case TEXT_EMOTE_WAVE:
                return EMOTE_ONESHOT_WAVE;
            case TEXT_EMOTE_BOW:
                return EMOTE_ONESHOT_BOW;
            case TEXT_EMOTE_DANCE:
                return EMOTE_ONESHOT_DANCE;
            case TEXT_EMOTE_CHEER:
                return EMOTE_ONESHOT_CHEER;
            case TEXT_EMOTE_SALUTE:
                return EMOTE_ONESHOT_SALUTE;
            case TEXT_EMOTE_APPLAUD:
                return EMOTE_ONESHOT_APPLAUD;
            case TEXT_EMOTE_KISS:
                return EMOTE_ONESHOT_KISS;
            case TEXT_EMOTE_FLEX:
                return EMOTE_ONESHOT_FLEX;
            case TEXT_EMOTE_LAUGH:
                return EMOTE_ONESHOT_LAUGH;
            case TEXT_EMOTE_NOD:
                return EMOTE_ONESHOT_YES;
            case TEXT_EMOTE_POINT:
                return EMOTE_ONESHOT_POINT;
            case TEXT_EMOTE_ROAR:
                return EMOTE_ONESHOT_ROAR;
            default:
                return 0;
        }
    }
}

namespace CityLife
{
    CustomSocial& CustomSocial::Instance()
    {
        static CustomSocial instance;
        return instance;
    }

    void CustomSocial::LoadConfig()
    {
        _enabled = sConfigMgr->GetOption<bool>("CityLife.Enable", true) &&
                   sConfigMgr->GetOption<bool>("CityLife.SocialReaction.Enable", true);
        _reactionsEnabled = sConfigMgr->GetOption<bool>("CityLife.SocialReaction.Reactions.Enable", true);
        _reactionChance = std::min<uint32>(100,
            sConfigMgr->GetOption<uint32>("CityLife.SocialReaction.Chance", 80));
        _reactionCooldownSeconds = std::clamp<uint32>(
            sConfigMgr->GetOption<uint32>("CityLife.SocialReaction.CooldownSeconds", 15), 3, 300);
        _reactionRange = sConfigMgr->GetOption<float>("CityLife.SocialReaction.Range", 25.0f);
        _reactionRange = std::isfinite(_reactionRange) ? std::clamp(_reactionRange, 5.0f, 60.0f) : 25.0f;
    }

    bool CustomSocial::IsEligible(Player* player) const
    {
        if (!player || !player->GetSession() || !player->IsInWorld() || !player->IsAlive() ||
            player->IsInCombat() || player->GetVictim() || player->duel || player->GetGroup() ||
            player->IsInFlight() || player->IsMounted() || player->GetTransport() ||
            player->HasUnitState(UNIT_STATE_LOST_CONTROL | UNIT_STATE_NOT_MOVE) ||
            player->IsNonMeleeSpellCast(false) || player->GetTradeData() || ::IsRealPlayer(player))
            return false;

        PlayerbotAI* ai = GET_PLAYERBOT_AI(player);
        return ai && !ai->HasGameClientMaster();
    }

    void CustomSocial::OnTextEmote(Player* sender, uint32 textEmote, ObjectGuid targetGuid)
    {
        if (!_enabled || !_reactionsEnabled || !sender || !::IsRealPlayer(sender) || !sender->IsInWorld())
            return;

        if (!ReactionEmote(textEmote))
            return;

        std::lock_guard<std::mutex> lock(_pendingMutex);
        _pendingEmotes.push_back({
            sender->GetGUID().GetCounter(),
            textEmote,
            SocialTime() + 5,
            targetGuid
        });
    }

    void CustomSocial::Remove(uint32 botGuid)
    {
        _botCooldownUntil.erase(botGuid);
        _eligibleBots.erase(botGuid);
    }

    void CustomSocial::ProcessReactions(uint32 now)
    {
        std::vector<PendingEmote> pending;
        {
            std::lock_guard<std::mutex> lock(_pendingMutex);
            pending.swap(_pendingEmotes);
        }

        if (pending.empty())
            return;

        for (PendingEmote const& emote : pending)
        {
            if (now > emote.ExpiresAt)
                continue;

            Player* sender = FindSocialPlayer(emote.Sender);
            if (!sender || !sender->IsInWorld() || !sender->IsAlive())
                continue;

            // Direct target reaction or nearby resident reaction
            Player* bot = nullptr;
            if (!emote.Target.IsEmpty() && emote.Target.IsPlayer())
            {
                uint32 const targetCounter = emote.Target.GetCounter();
                if (_eligibleBots.count(targetCounter) || sCityLifeMgr.IsResident(targetCounter))
                    bot = ObjectAccessor::FindPlayer(emote.Target);
            }

            if (!bot)
                continue;

            uint32 const botGuidLow = bot->GetGUID().GetCounter();
            if (_botCooldownUntil[botGuidLow] > now)
                continue;

            if (!IsEligible(bot) || !bot->IsWithinDistInMap(sender, _reactionRange) ||
                !bot->CanSeeOrDetect(sender) || !bot->IsWithinLOSInMap(sender))
                continue;

            if (!roll_chance_i(_reactionChance))
                continue;

            uint32 const reactionAnim = ReactionEmote(emote.TextEmote);
            if (!reactionAnim)
                continue;

            bot->SetFacingToObject(sender);
            bot->HandleEmoteCommand(reactionAnim);
            _botCooldownUntil[botGuidLow] = now + _reactionCooldownSeconds;
        }
    }

    void CustomSocial::Update(std::vector<uint32> const& eligibleBotGuids)
    {
        if (!_enabled)
            return;

        uint32 const now = SocialTime();
        _eligibleBots.clear();
        _eligibleBots.insert(eligibleBotGuids.begin(), eligibleBotGuids.end());

        if (now >= _nextPruneAt)
        {
            _nextPruneAt = now + 60;
            std::erase_if(_botCooldownUntil, [now](auto const& entry) { return entry.second <= now; });
        }

        if (_reactionsEnabled)
            ProcessReactions(now);
    }
}
