# Architecture Specification: `mod-cities-conflicts`

This document details the software architecture, runtime state machines, shared reservation protocols, and wire transport mechanisms of the unified **Cities & Conflicts** module.

---

## 1. High-Level Subsystems

`mod-cities-conflicts` is structured into four cooperative subsystems:

```
+-----------------------------------------------------------------------------------+
|                            mod-cities-conflicts                                   |
|                                                                                   |
|  [City Life Engine]                  [World Conflicts Engine]                     |
|  - CityLifeMgr                       - PvPLifeMgr                                 |
|  - Civic Activities & Vendors        - 35+ Frontline Hotspots                     |
|  - TortoiseBots WorkIdle Policy      - Capital Gate Duel Arenas                   |
|  - TortoiseBots RpgMixer Policy      - Reactive Capital Raid Defenses             |
|         |                                    |                                    |
|         +-----------------+------------------+                                    |
|                           |                                                       |
|                           v                                                       |
|             [LifeBotReservation Registry]                                         |
|             - Mutual Anti-Stealing Barrier                                        |
|             - Thread-Safe Shared Leases                                           |
|                           |                                                       |
|                           v                                                       |
|             [LifeTelemetryBridge Engine]                                          |
|             - Binary Fragmenter & CRC32                                           |
|             - CLIFE / PVP Wire Streams                                            |
+---------------------------|-------------------------------------------------------+
                            | SendAddonMessage
                            v
+-----------------------------------------------------------------------------------+
|               CitiesConflictsDashboard (WotLK 3.3.5a Client AddOn)                |
|  - Real-time Census, District Overviews, Duel Tracker, Bot Activity Inspector     |
+-----------------------------------------------------------------------------------+
```

---

## 2. City Life Engine

### Civic District Management
- Governs 16+ urban hubs across Eastern Kingdoms, Kalimdor, Outland, and Northrend.
- Dynamic time-of-day population scaling adjusting citizen presence across morning, day, evening, and night.
- Natural pathing routines with water-depth and canal avoidance (preventing bots falling into Stormwind canals).

### Behavior Modules
1. **`CityLifeActivities`**: Manages vendor shopping, tavern dining, plaza socializing, and district touring.
2. **`CityLifeBeggarTrade`**: Low-wealth citizens requesting copper from passing players/bots with authentic responses.
3. **`CityLifeCustomSocial`**: Emote interactions, conversation gestures, and weapon sheathing.
4. **`CityLifeHumanBehavior`**: Authentic idle behaviors: weapon unsheathing, inspecting items, summoning vanity pets, sitting on benches.
5. **`CityLifeWorkIdlePolicy`**: TortoiseBots-inspired anti-stall policy ensuring bots never get permanently stuck in infinite loops.
6. **`CityLifeRpgMixerPolicy`**: TortoiseBots-inspired weighted RPG routine mixing.

---

## 3. World Conflicts Engine

### Frontline Hotspots & Reactive Defense
- 35+ outdoor skirmish zones where Alliance and Horde playerbots engage in natural PvP combat.
- Reactive raid defense: Detects player-led invasion forces heading toward faction leaders, staging an opposing defender force in formation lanes.

### Capital Gate Duel Arenas
- Concentrated duel grounds outside Stormwind and Orgrimmar gates, as well as Ironforge, Undercity, and Dalaran Underbelly.
- Staging lattice: Angular approach paths, spectator gathering, and proximity-prioritized challenger selection.
- Player interaction: Bots in duel grounds issue challenges to nearby consenting players within level ranges.

---

## 4. Shared Reservation System (`LifeBotReservation.h`)

To prevent conflicts where City Life and World Conflicts simultaneously command the same playerbot:
- `PlayerbotsLife::ReservationRegistry` maintains atomic ownership leases per bot GUID.
- If a bot is leased by City Life, World Conflicts cannot recruit it for a duel or skirmish.
- If a bot is engaged in a duel or PvP skirmish, City Life cannot assign it a civic task.
- Unconditional release hooks: If a bot is invited to a human player group, enters master combat, or logs out, both subsystems immediately release reservations.

---

## 5. Telemetry Bridge & Client AddOn

- Server sends compact serialized state packets over `CLIFE` and `PVP` message channels.
- Paged transmission with 8-character hex CRC32 verification ensures packets up to 255 bytes reassemble flawlessly on the client.
- The bundled AddOn ([`addon/CitiesConflictsDashboard/`](../addon/CitiesConflictsDashboard/)) displays:
  - **Overview**: Combined server bot census, faction balance, and district occupancy.
  - **City Life**: Real-time breakdown of citizens per city, district, and active task.
  - **PvP Life**: Active duel matches, queue contenders, and frontline skirmish statuses.
