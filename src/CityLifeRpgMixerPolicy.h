/*
 * Living Cities - Weighted RPG Mixer Policy
 * Inspired by TortoiseBots (Turtle WoW / CMangos) RpgMixerPolicy.h
 * Copyright (C) 2026 iCore
 * SPDX-License-Identifier: GPL-2.0-or-later
 */

#ifndef CITY_LIFE_RPG_MIXER_POLICY_H
#define CITY_LIFE_RPG_MIXER_POLICY_H

#include "CityLifeTypes.h"
#include "Random.h"
#include <cstdint>
#include <vector>

namespace CityLife
{
    enum class CityLeisureSlot : uint8
    {
        Social = 0,
        Tavern = 1,
        MarketCommerce = 2,
        Crafting = 3,
        WanderPatrol = 4,
        Count = 5
    };

    struct RpgMixerWeights
    {
        uint32 SocialWeight = 35;
        uint32 TavernWeight = 25;
        uint32 MarketCommerceWeight = 20;
        uint32 CraftingWeight = 10;
        uint32 WanderPatrolWeight = 10;
    };

    /**
     * @brief Weighted RPG activity chooser for living city residents.
     * Prevents monotonous repetition and introduces natural variety into bot day cycles.
     */
    class RpgMixerPolicy
    {
    public:
        static CityLeisureSlot RollSlot(RpgMixerWeights const& weights)
        {
            uint32 const totalWeight = weights.SocialWeight +
                                       weights.TavernWeight +
                                       weights.MarketCommerceWeight +
                                       weights.CraftingWeight +
                                       weights.WanderPatrolWeight;

            if (totalWeight == 0)
                return CityLeisureSlot::WanderPatrol;

            uint32 roll = urand(1, totalWeight);

            if (roll <= weights.SocialWeight)
                return CityLeisureSlot::Social;
            roll -= weights.SocialWeight;

            if (roll <= weights.TavernWeight)
                return CityLeisureSlot::Tavern;
            roll -= weights.TavernWeight;

            if (roll <= weights.MarketCommerceWeight)
                return CityLeisureSlot::MarketCommerce;
            roll -= weights.MarketCommerceWeight;

            if (roll <= weights.CraftingWeight)
                return CityLeisureSlot::Crafting;

            return CityLeisureSlot::WanderPatrol;
        }

        static CitizenActivity SlotToActivity(CityLeisureSlot slot, CityPoiType currentPoi)
        {
            switch (slot)
            {
                case CityLeisureSlot::Social:
                    return (currentPoi == CityPoiType::Plaza) ? CitizenActivity::PlazaSocial : CitizenActivity::CrowdSocial;
                case CityLeisureSlot::Tavern:
                    return (urand(0, 1) == 0) ? CitizenActivity::SitInTavern : CitizenActivity::DrinkInTavern;
                case CityLeisureSlot::MarketCommerce:
                    return (urand(0, 1) == 0) ? CitizenActivity::VisitAuctionHouse : CitizenActivity::BuyFood;
                case CityLeisureSlot::Crafting:
                    return CitizenActivity::VisitTrainer;
                case CityLeisureSlot::WanderPatrol:
                default:
                    return CitizenActivity::WanderDistrict;
            }
        }
    };
}

#endif // CITY_LIFE_RPG_MIXER_POLICY_H
