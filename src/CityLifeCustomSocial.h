/*
 * Living Cities - Bidirectional Social & Emote Reaction Engine
 * Copyright (C) 2026 iCore
 * SPDX-License-Identifier: GPL-2.0-or-later
 */

#ifndef CITY_LIFE_CUSTOM_SOCIAL_H
#define CITY_LIFE_CUSTOM_SOCIAL_H

#include "Define.h"
#include "ObjectGuid.h"

#include <mutex>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

class Player;

namespace CityLife
{
    class CustomSocial
    {
    public:
        static CustomSocial& Instance();

        void LoadConfig();
        // Call on the world thread with idle city residents.
        void Update(std::vector<uint32> const& eligibleBotGuids);
        // Map-thread hook queues GUIDs for safe execution on the world thread.
        void OnTextEmote(Player* sender, uint32 textEmote, ObjectGuid targetGuid);
        void Remove(uint32 botGuid);

    private:
        struct PendingEmote
        {
            uint32 Sender = 0;
            uint32 TextEmote = 0;
            uint32 ExpiresAt = 0;
            ObjectGuid Target;
        };

        CustomSocial() = default;

        bool IsEligible(Player* player) const;
        void ProcessReactions(uint32 now);

        bool _enabled = true;
        bool _reactionsEnabled = true;
        uint32 _reactionChance = 80;
        uint32 _reactionCooldownSeconds = 15;
        float _reactionRange = 25.0f;
        uint32 _nextPruneAt = 0;

        std::unordered_set<uint32> _eligibleBots;
        std::unordered_map<uint32, uint32> _botCooldownUntil;
        std::unordered_map<uint32, uint32> _senderCooldownUntil;
        std::mutex _pendingMutex;
        std::vector<PendingEmote> _pendingEmotes;
    };
}

#define sCityLifeCustomSocial CityLife::CustomSocial::Instance()

#endif // CITY_LIFE_CUSTOM_SOCIAL_H
