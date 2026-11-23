# Issues & Defect Registry: `mod-cities-conflicts`

This document tracks all registered, active, and resolved defects for the unified `mod-cities-conflicts` module ecosystem.

| Issue ID | Severity | Status | Title / Summary | Resolution Notes |
|---|---|---|---|---|
| CC-001 | High | RESOLVED | Unification of `mod-living-cities` and `mod-world-conflicts` | Successfully merged both subsystems into single sovereign module with shared `LifeBotReservation` and `LifeTelemetryBridge`. |
| CC-002 | Medium | RESOLVED | Built-in AddOn inclusion | Bundled `CitiesConflictsDashboard` under `addon/CitiesConflictsDashboard/` with protocol handlers for both `CLIFE` and `PVP` prefixes. |
| CC-003 | Medium | RESOLVED | TortoiseBots Policy Integration | Ported `WorkIdlePolicy` (30s anti-stall timeout) and `RpgMixerPolicy` (weighted leisure activity mixer) into city resident loops. |
| CC-004 | Low | RESOLVED | Beggar charity trade & human behavior immersion | Ported `BeggarTrade` charity gifting and `HumanBehavior` (inspect, weapon sheathing, companion vanity pets, ambient sitting) with zero core modifications. |
