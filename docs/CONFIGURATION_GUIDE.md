# Configuration Guide: `mod-cities-conflicts`

This guide explains the primary configuration sections in [`conf/mod_cities_conflicts.conf.dist`](../conf/mod_cities_conflicts.conf.dist).

---

## 1. City Life Settings

| Directive | Type | Default | Description |
|---|---|---|---|
| `CityLife.Enable` | Boolean | `1` | Master toggle for the entire City Life subsystem. |
| `CityLife.Debug` | Boolean | `0` | Outputs verbose diagnostic messages to worldserver console. |
| `CityLife.MaxBotsPerCity` | Integer | `30` | Maximum simultaneous citizen bots in any single capital. |
| `CityLife.OverallBorrowRatio` | Float | `0.10` | Maximum fraction of the natural playerbot pool borrowed (10%). |
| `CityLife.AntiStallTimeout` | Integer | `120` | Seconds before an idle or blocked bot is redirected. |
| `CityLife.Weight.MarketShopping` | Integer | `25` | Relative probability weight for visiting market stalls. |
| `CityLife.Weight.TavernSocial` | Integer | `20` | Relative probability weight for patronizing inns. |
| `CityLife.Weight.ClassTrainer` | Integer | `15` | Relative probability weight for visiting class trainers. |

---

## 2. World Conflicts Settings

| Directive | Type | Default | Description |
|---|---|---|---|
| `PvPLife.Enable` | Boolean | `1` | Master toggle for the World Conflicts subsystem. |
| `PvPLife.Debug` | Boolean | `0` | Outputs verbose PvP diagnostic messages to worldserver console. |
| `PvPLife.OverallBorrowRatio` | Float | `0.10` | Maximum fraction of playerbot pool recruited for PvP (10%). |
| `PvPLife.Duel.Enable` | Boolean | `1` | Enables capital gate duel arenas. |
| `PvPLife.Duel.ChallengePlayer` | Boolean | `1` | Allows dueling bots to challenge real players near gates. |
| `PvPLife.Duel.MaxLevelDifference`| Integer | `5` | Maximum level disparity between duel contenders. |
| `PvPLife.Hotspots.Enable` | Boolean | `1` | Enables outdoor frontline skirmish hotspots. |
| `PvPLife.ReactiveDefense.Enable`| Boolean | `1` | Stages defender counter-attacks against city invasion raids. |

---

## 3. Shared Reservation & Telemetry Settings

| Directive | Type | Default | Description |
|---|---|---|---|
| `Life.Reservation.TimeoutSeconds` | Integer | `300` | Lease timeout before an unresponsive bot is returned to pool. |
| `Life.Telemetry.Enable` | Boolean | `1` | Streams live census and activity state to client AddOn. |
| `Life.Telemetry.IntervalMs` | Integer | `1000` | Telemetry broadcast refresh rate in milliseconds. |
