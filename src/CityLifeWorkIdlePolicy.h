/*
 * Living Cities - WorkIdle Policy
 * Inspired by TortoiseBots (Turtle WoW / CMangos) WorkIdlePolicy.h
 * Copyright (C) 2026 iCore
 * SPDX-License-Identifier: GPL-2.0-or-later
 */

#ifndef CITY_LIFE_WORK_IDLE_POLICY_H
#define CITY_LIFE_WORK_IDLE_POLICY_H

#include <cstdint>

namespace CityLife
{
    // Default stale horizon: 30 seconds of inactivity at a workstation or destination
    // releases the hold so the resident does not get frozen indefinitely.
    constexpr uint32 kDefaultWorkIdleReleaseSec = 30;

    /**
     * @brief Evaluates whether a resident's current workstation or activity hold has gone stale.
     * @param anchorTimeMs Timestamp when the bot arrived or started its current activity phase.
     * @param nowMs Current monotonic game time in milliseconds.
     * @param hasInteraction True if the bot is actively conversing, trading, or casting.
     * @param hasAttackers True if the bot has entered combat.
     * @param horizonSec Inactivity threshold in seconds (defaults to 30s).
     * @return True if the activity hold has timed out and should be released.
     */
    inline bool IsWorkIdleStale(uint32 anchorTimeMs, uint32 nowMs,
                                bool hasInteraction, bool hasAttackers,
                                uint32 horizonSec = kDefaultWorkIdleReleaseSec)
    {
        if (anchorTimeMs == 0)
            return false;

        if (hasAttackers)
            return true; // Combat immediately invalidates civilian work holds

        if (hasInteraction)
            return false; // Active dialogue or trade keeps hold alive

        uint32 const elapsedSec = (nowMs >= anchorTimeMs) ? (nowMs - anchorTimeMs) / 1000 : 0;
        return elapsedSec >= horizonSec;
    }
}

#endif // CITY_LIFE_WORK_IDLE_POLICY_H
