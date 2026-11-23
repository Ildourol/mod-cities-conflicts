# Cities & Conflicts (`mod-cities-conflicts`)

Unified AzerothCore module combining **Urban Life Simulation** and **World PvP Conflicts**, accompanied by the built-in **`CitiesConflictsDashboard`** WotLK 3.3.5a client AddOn.

---

## Architecture Overview

1. **City Life Domain (`CityLifeMgr`)**:
   - Manages urban bot quotas, dynamic day/night time scaling, civic district hubs (Stormwind, Orgrimmar, Ironforge, Undercity, Dalaran, Shattrath, Goldshire).
   - Activity loops: Market Vendors, Plaza Social, Crowd Social, Crafting Work, Tavern Drinking, Inn Rest, Beggar Charity Trades, Human Behavior (inspect, weapon sheathing, vanity pets, sitting).
   - TortoiseBots-inspired **WorkIdle Anti-Stall Policy** and **Weighted RPG Mixer Policy**.

2. **World Conflicts Domain (`PvPLifeMgr`)**:
   - Dynamic world PvP hotspots, capital raids, open-world skirmishes, persistent duel zones (outside Stormwind Gates & Orgrimmar).
   - Safe bot lease arbitration (`LifeBotReservation.h`) preventing combat bot vs citizen role conflicts.

3. **Telemetry & Client AddOn (`LifeTelemetryBridge` & `CitiesConflictsDashboard`)**:
   - Binary wire protocol (`CLIFE` & `PVP` prefixes) streaming real-time live bot census, zone occupancy, active skirmishes, and task details to the client UI.
   - Client AddOn located under [`addon/CitiesConflictsDashboard/`](addon/CitiesConflictsDashboard/).

---

## Configuration

All configuration directives are consolidated in [`conf/mod_cities_conflicts.conf.dist`](conf/mod_cities_conflicts.conf.dist). Copy to your server's configuration directory as `mod_cities_conflicts.conf`.
