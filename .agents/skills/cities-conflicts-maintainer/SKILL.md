---
name: cities-conflicts-maintainer
description: Maintain, configure, and audit mod-cities-conflicts for AzerothCore 3.3.5a, managing urban bot schedules, world PvP hotspots, capital gate duels, telemetry serialization, and the bundled CitiesConflictsDashboard client AddOn.
---

# Cities & Conflicts Maintainer Skill

This skill defines the workflows, diagnostic procedures, and architectural standards for maintaining `mod-cities-conflicts`.

## 1. Scope & Core Invariants
- **Two Core Pillars Immutability**: Never modify `azerothcore-wotlk` or `mod-playerbots`. All behaviors, reservations, and hooks reside in `mod-cities-conflicts`.
- **Shared Reservation Integrity**: `PlayerbotsLife::ReservationRegistry` prevents bot role collisions between civic activities and PvP skirmishes.
- **Client Protocol Consistency**: Ensure telemetry payload encoding (`CLIFE` and `PVP` channels) strictly matches `addon/CitiesConflictsDashboard/Protocol.lua`.

## 2. Configuration Subsystems
Configuration directives in `conf/mod_cities_conflicts.conf.dist`:
- `CityLife.Enable`: Master switch for urban simulation.
- `CityLife.Population.Stormwind.*`, `CityLife.Population.Orgrimmar.*`: District-level citizen quotas.
- `PvPLife.Enable`: Master switch for world PvP skirmishes and duel arenas.
- `PvPLife.Duel.Enable`: Master switch for capital gate bot dueling.
- `PvPLife.Hotspot.*`: Frontline conflict hotspot parameters.

## 3. In-Game Diagnostics & GM Commands
- `.citylife status`: View live hub occupancy, district distributions, and citizen quotas.
- `.citylife reload`: Hot-reload civic schedules and configuration without server restart.
- `.pvplife status`: Inspect active frontline skirmishes and duel grounds.
- `.pvplife duel list`: Display active duel pairings and queue states.

## 4. Verification & Testing
Run the automated regression test suite:
```powershell
python -m unittest discover -s "mod-cities-conflicts/tests" -p "test_*.py"
```
Validates:
- Real Lua 5.1 / LuaJIT execution of client AddOn code.
- CRC32 checksum generation and paged fragment reassembly.
- Zone and hub DBC compatibility.
