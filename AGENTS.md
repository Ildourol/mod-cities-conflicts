# AI Agent Operating Guidelines: `mod-cities-conflicts`

This document defines sovereign agent operating rules, architectural invariants, subsystem coordination protocols, C++ threading invariants, database standards, and verification procedures for the unified **Cities & Conflicts** module (`mod-cities-conflicts`).

---

## 1. Prime Directive: The Two Core Pillars Immutability Doctrine

> [!CAUTION]
> **STRICT IMMUTABILITY RULE**:
> * **`azerothcore-wotlk`** is the core server engine repository and must **NEVER** be edited.
> * **`mod-playerbots`** is the companion AI bot engine and must **NEVER** be edited.
> * All bot behavior scheduling, urban simulation, world PvP conflicts, capital gate duels, wire telemetry, and UI dashboard coordination must reside **100% inside this module**.
>
> Any proposed direct patch to core or `mod-playerbots` is an architectural violation. Agents must use public hooks (`ScriptMgr`, `sPlayerbotAIConfig`, `PlayerbotAI::ChangeStrategy`, `PlayerbotAI::DoSpecificAction`) and the in-module reservation registry.

---

## 2. Architecture & Subsystems

`mod-cities-conflicts` unifies the autonomous urban simulation from `mod-living-cities` and dynamic world PvP/dueling from `mod-world-conflicts` into a single cohesive runtime, served by a bundled client AddOn.

```
+-----------------------------------------------------------------------------------+
|                            mod-cities-conflicts                                   |
|                                                                                   |
|  +------------------------------+             +--------------------------------+  |
|  |     City Life Subsystem      |             |   World Conflicts Subsystem    |  |
|  |  - CityLifeMgr               |             |  - PvPLifeMgr                  |  |
|  |  - CityLifeActivities        |             |  - PvPLifeDuelSelection        |  |
|  |  - CityLifeBeggarTrade       |             |  - PvPLifeDuelRequestPolicy    |  |
|  |  - CityLifeCustomSocial      |             |  - PvPLifeAudit                |  |
|  |  - CityLifeHumanBehavior     |             +---------------+----------------+  |
|  |  - CityLifeMovement          |                             |                   |
|  |  - WorkIdlePolicy (Tortoise) |                             |                   |
|  |  - RpgMixerPolicy (Tortoise) |                             |                   |
|  +--------------+---------------+                             |                   |
|                 |                                             |                   |
|                 +----------------------+----------------------+                   |
|                                        |                                          |
|                                        v                                          |
|                     +------------------------------------+                        |
|                     |     LifeBotReservation.h           |                        |
|                     | (Mutual Anti-Stealing Registry)    |                        |
|                     +------------------+-----------------+                        |
|                                        |                                          |
|                                        v                                          |
|                     +------------------------------------+                        |
|                     |     LifeTelemetryBridge.h          |                        |
|                     | (CLIFE & PVP Packet Serialization) |                        |
|                     +------------------+-----------------+                        |
+----------------------------------------|------------------------------------------+
                                         | Addon Channel (SendAddonMessage)
                                         v
+-----------------------------------------------------------------------------------+
|                 Client AddOn: addon/CitiesConflictsDashboard                      |
|  - Real-time Census, District Maps, Bot Inspector, Skirmish Radar, GM Controls    |
+-----------------------------------------------------------------------------------+
```

### A. Subsystem Roles
1. **City Life Domain (`CityLifeMgr`)**:
   - Manages urban bot quotas, dynamic day/night time scaling, civic district hubs (Stormwind, Orgrimmar, Ironforge, Undercity, Darnassus, Thunder Bluff, Exodar, Silvermoon, Shattrath, Dalaran, Gadgetzan, Goldshire, Honor Hold, Thrallmar).
   - Civic activities: Market shopping, tavern dining, plaza social, guild visits, class trainers, fishing at docks, visiting mailboxes, bank/auctioneer visits.
   - Micro-behaviors: Beggar charity trades, item inspection, weapon sheathing, vanity pets, sitting on benches, emote dialogues.
   - TortoiseBots policies: Anti-stall WorkIdle timing and weighted RPG routine mixing.
2. **World Conflicts Domain (`PvPLifeMgr`)**:
   - 35+ outdoor PvP skirmish hotspots across Azeroth, Outland, and Northrend.
   - Reactive capital raid defense (formation staging and engagement).
   - Capital gate duel arenas (Stormwind, Orgrimmar, Ironforge, Undercity, Dalaran Underbelly) with angular approach pathing, spectator crowd gathering, and player duel challenges.
3. **Mutual Anti-Stealing Reservation (`LifeBotReservation.h`)**:
   - Thread-safe registry (`PlayerbotsLife::ReservationRegistry`) ensuring bots reserved for civic duties are never recruited into duels or skirmishes, and vice versa.
4. **Telemetry & Client AddOn (`LifeTelemetryBridge.h` & `addon/CitiesConflictsDashboard/`)**:
   - Dispatches paged wire snapshots (`CLIFE` and `PVP` prefixes) with CRC32 integrity verification.
   - Client AddOn provides live census, district breakdown, active skirmish tracking, and bot inspection.

---

## 3. Sovereign Invariants & Safety Protocols

1. **Zero Bot Tampering**:
   - Bots are borrowed strictly AS-IS from the natural `mod-playerbots` pool.
   - Never artificially modify bot levels, stats, talents, or inventories.
2. **Conservative Population Budget**:
   - Default borrowing budget of 10% / 120 bots max per subsystem guarantees that ≥ 80% of playerbots remain completely free for natural open-world questing, dungeons, and leveling.
3. **Instant Disengagement**:
   - If a citizen or dueling bot is invited to a player group, commanded by its master, enters combat, or logs out, it immediately vacates module tasks and restores its default AI state.
4. **Zero GM Spam**:
   - Game Masters are strictly exempt from duel challenges, beggar whispers, or automated yells.
5. **Silent-by-Default Operation**:
   - Ambient chatter, announcements, and beggar dialogues default to OFF (`0`) in config for a clean player experience out of the box.

---

## 4. Directory Layout

```text
mod-cities-conflicts/
├── CMakeLists.txt                 # Module CMake linkage definitions
├── README.md                      # Public documentation and overview
├── module-info.json               # Module metadata and dependencies
├── LICENSE                        # GPL v2 license
├── AGENTS.md                      # Sovereign agent guidelines
├── .agents/
│   └── skills/
│       └── cities-conflicts-maintainer/
│           └── SKILL.md           # Maintainer skill
├── conf/
│   └── mod_cities_conflicts.conf.dist # Master consolidated configuration
├── data/
│   └── sql/
│       ├── manual/                # Base schemas for city_life_hub & world_pvp_life
│       └── world/updates/         # Idempotent incremental migrations (13 scripts)
├── src/
│   ├── cities_conflicts_loader.cpp# Exported script loader
│   ├── mod_cities_conflicts.cpp   # Core subsystem initialization & telemetry registration
│   ├── LifeBotReservation.h       # Shared reservation registry
│   ├── LifeTelemetryBridge.h      # Paged wire protocol bridge
│   ├── CityLife*.{h,cpp}          # City Life subsystem sources
│   └── PvPLife*.{h,cpp}           # World Conflicts subsystem sources
├── addon/
│   └── CitiesConflictsDashboard/  # Client AddOn (TOC, Locales, UI tabs, Store, Protocol)
└── tests/
    ├── test_dashboard_protocol.py # AddOn protocol, CRC32, LuaJIT parsing tests
    ├── test_duel_assets.py        # Duel assets and zone validity tests
    ├── test_native_hub_data.py    # City hub seed and zone ID tests
    └── test_*.cpp                 # Standalone C++ policy tests
```

---

## 5. Verification & Testing Standards

Whenever modifying `mod-cities-conflicts`:
1. **Python Unit Tests**:
   Execute the non-server regression suite:
   ```bash
   python -m unittest discover -s tests -p "test_*.py"
   ```
   Must pass 100% of tests (protocol parsing, CRC32 calculation, zone/hub DBC checks).
2. **Compilation**:
   Ensure CMake discovers `mod-cities-conflicts` and that `worldserver` compiles with zero errors.
3. **Database Idempotency**:
   All SQL scripts under `data/sql/` must use `IF NOT EXISTS`, `INSERT IGNORE`, or `ON DUPLICATE KEY UPDATE`.
