#!/usr/bin/env python3
"""
CitiesConflictsDashboard Regression Test Suite
Executes real Lua 5.1/LuaJIT code via lupa with real server protocol fixtures.
Validates:
- Clean empty initialization (no invented/fake data)
- Protocol encoding/decoding, CRC32, chunking/assembly
- Handshake & permissions (case-insensitive tiers, 'all' capabilities)
- Capacity, Roster, Hubs, Zones, Queues parsing
- Snapshot generation pruning (dead/departed bots removed)
- Bot detail querying and caching
- Error and corrupted packet handling
"""

import os
import unittest
import zlib
from lupa.luajit21 import LuaRuntime

class TestCitiesConflictsDashboardProtocol(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lua = LuaRuntime(unpack_returned_tuples=True)
        
        # Setup WoW 3.3.5 / Lua 5.1 mock environment
        cls.lua.execute("""
            _G = _G or {}
            loadstring = loadstring or load
            time = time or os.time
            table = table or {}
            string = string or {}
            math = math or {}


            -- Mock WoW frame and chat
            DEFAULT_CHAT_FRAME = {
                AddMessage = function(self, msg)
                    -- print("[WOW_CHAT]", msg)
                end
            }

            local mockTime = 1000.0
            function GetTime()
                return mockTime
            end
            function SetMockTime(t)
                mockTime = t
            end

            function UnitName(unit)
                if unit == "player" then return "AdminPlayer" end
                return nil
            end

            function GetRealmName()
                return "AzerothCore"
            end

            function UnitExists(unit) return false end
            function UnitIsPlayer(unit) return false end
            function UnitIsUnit(u1, u2) return u1 == u2 end
            function UnitGUID(unit) return nil end
            function UnitClass(unit) return "Warrior", "WARRIOR" end
            function UnitLevel(unit) return 80 end
            function UnitFactionGroup(unit) return "Alliance" end
            function UnitAffectingCombat(unit) return false end
            function GetZoneText() return "Stormwind City" end
            function GetSubZoneText() return "Trade District" end
            function GetNumPartyMembers() return 0 end
            function GetNumRaidMembers() return 0 end

            outboundAddonMessages = {}
            function SendAddonMessage(prefix, message, channel, target)
                table.insert(outboundAddonMessages, {
                    prefix = prefix,
                    message = message,
                    channel = channel,
                    target = target
                })
            end

            function CreateFrame(frameType, name, parent, template)
                local frame = {
                    name = name,
                    scripts = {},
                    events = {},
                    SetScript = function(self, scriptType, fn)
                        self.scripts[scriptType] = fn
                    end,
                    RegisterEvent = function(self, evt)
                        self.events[evt] = true
                    end,
                    UnregisterEvent = function(self, evt)
                        self.events[evt] = nil
                    end,
                    SetWidth = function() end,
                    SetHeight = function() end,
                    SetPoint = function() end,
                    SetAllPoints = function() end,
                    Show = function() end,
                    Hide = function() end,
                    GetWidth = function() return 1000 end,
                    GetHeight = function() return 600 end,
                    CreateFontString = function(self, name, layer, font)
                        return {
                            SetPoint = function() end,
                            SetText = function(self, txt) self.text = txt end,
                            text = ""
                        }
                    end
                }
                return frame
            end

            -- Global addon table mock
            LifeDashboard = {
                L = {},
                connected = false,
                connectionState = "DISCONNECTED",
                sessionEpoch = nil,
                lastPacketTime = 0,
                isMockData = false,
                Window = {
                    UpdateHeaderStatus = function() end,
                    OpenDrawer = function() end
                }
            }
            _G["CitiesConflictsDashboard"] = LifeDashboard
            _G["PlayerbotsLifeDashboard"] = LifeDashboard
        """)

        # Load addon source files in TOC order
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "addon", "CitiesConflictsDashboard"))
        files_to_load = [
            "Locales/enUS.lua",
            "Compat.lua",
            "Clock.lua",
            "Permissions.lua",
            "Protocol.lua",
            "Store.lua",
            "UI/Widgets.lua",
            "UI/Overview.lua",
            "UI/CityLife.lua",
            "UI/PvPLife.lua"
        ]

        for rel_path in files_to_load:
            file_path = os.path.join(base_dir, rel_path)
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()
            # Wrap as addon file loader chunk (... is ADDON_NAME, LifeDashboard)
            load_wrapper = f"""
                local func, err = loadstring([=====[{code}]=====], "{rel_path}")
                if not func then error("Failed loading {rel_path}: " .. tostring(err)) end
                func("CitiesConflictsDashboard", LifeDashboard)
            """
            cls.lua.execute(load_wrapper)

    def setUp(self):
        # Reset state before each test
        self.lua.execute("""
            outboundAddonMessages = {}
            LifeDashboard.connected = false
            LifeDashboard.connectionState = "DISCONNECTED"
            LifeDashboard.sessionEpoch = nil
            LifeDashboard.Protocol:ResetBuffers()
            LifeDashboard.Permissions:Reset()
            LifeDashboard.Store:InitWorld()
        """)

    def test_01_clean_empty_initialization(self):
        """Verify Store:InitWorld creates clean empty state with NO fake data."""
        self.lua.execute("LifeDashboard.Store:InitWorld()")
        
        has_server_cap = self.lua.eval("LifeDashboard.Store.hasServerCapacity")
        self.assertFalse(has_server_cap, "Store should not claim server capacity before handshake")
        
        bot_count = self.lua.eval("#LifeDashboard.Store.botList")
        self.assertEqual(bot_count, 0, "Initial botList must be empty (no fake bots)")
        
        hub_count = self.lua.eval("#LifeDashboard.Store.cityHubList")
        self.assertEqual(hub_count, 0, "Initial cityHubList must be empty")
        
        zone_count = self.lua.eval("#LifeDashboard.Store.pvpZoneList")
        self.assertEqual(zone_count, 0, "Initial pvpZoneList must be empty")
        
        queue_count = self.lua.eval("#LifeDashboard.Store.workQueues")
        self.assertEqual(queue_count, 0, "Initial workQueues must be empty")
        
        cap_total = self.lua.eval("LifeDashboard.Store.capacity.total")
        self.assertEqual(cap_total, 0, "Initial capacity total must be 0")

    def test_02_handshake_and_permissions(self):
        """Verify HELLO outbound and WELCOME inbound handshake with 'all' caps and normalized tier."""
        req_id = self.lua.eval("LifeDashboard.Protocol:SendMessage('HELLO', 'main', 1001, 'v=1.0.0;build=12340')")
        self.assertEqual(req_id, 1001)
        
        msg_count = self.lua.eval("#outboundAddonMessages")
        self.assertGreater(msg_count, 0, "Should have transmitted outbound message")
        
        sent_prefix = self.lua.eval("outboundAddonMessages[1].prefix")
        self.assertEqual(sent_prefix, "LIFE335")
        
        sent_channel = self.lua.eval("outboundAddonMessages[1].channel")
        self.assertEqual(sent_channel, "WHISPER")
        
        # Server responds with WELCOME: capabilities="all", tier="admin" (lowercase as sent by LifeTelemetryBridge)
        welcome_payload = "all|admin|1700000005000|1700000005"
        self.lua.execute(f"""
            LifeDashboard.Store:HandleMessage("WELCOME", "main", 1001, "sess_101", "{welcome_payload}")
        """)
        
        connected = self.lua.eval("LifeDashboard.connected")
        self.assertTrue(connected)
        
        session = self.lua.eval("LifeDashboard.sessionEpoch")
        self.assertEqual(session, "sess_101")
        
        # Verify permissions tier normalized to Admin
        tier = self.lua.eval("LifeDashboard.Permissions.currentTier")
        self.assertEqual(tier, "Admin")
        
        # Verify 'all' token enabled all individual capability flags
        self.assertTrue(self.lua.eval("LifeDashboard.Permissions.capabilities.cityLife"))
        self.assertTrue(self.lua.eval("LifeDashboard.Permissions.capabilities.pvpLife"))
        self.assertTrue(self.lua.eval("LifeDashboard.Permissions.capabilities.actionObserver"))
        self.assertTrue(self.lua.eval("LifeDashboard.Permissions.capabilities.operatorControls"))
        self.assertTrue(self.lua.eval("LifeDashboard.Permissions.capabilities.auditLogs"))
        self.assertTrue(self.lua.eval("LifeDashboard.Permissions:CanViewDiagnostics()"))
        self.assertTrue(self.lua.eval("LifeDashboard.Permissions:CanExecuteControls()"))

    def test_03_capacity_payload_real_and_empty(self):
        """Verify CAPACITY parsing with zero/empty values and live values."""
        # Connect first
        self.lua.execute('LifeDashboard.Store:HandleMessage("WELCOME", "main", 1, "s1", "all|admin|0|0")')
        
        # Zero capacity
        self.lua.execute('LifeDashboard.Store:HandleMessage("CAPACITY", "main", 1, "s1", "0|0|0|0|0|0|0|0|0|0")')
        self.assertTrue(self.lua.eval("LifeDashboard.Store.hasServerCapacity"))
        self.assertEqual(self.lua.eval("LifeDashboard.Store.capacity.total"), 0)
        self.assertEqual(self.lua.eval("LifeDashboard.Store.capacity.free"), 0)
        
        # Live capacity payload from server
        # Total: 1000, City(T:120, A:45, P:5, R:2), PvP(T:80, A:30, P:4, R:1), Free: 925
        live_cap = "1000|120|45|5|2|80|30|4|1|925"
        self.lua.execute(f'LifeDashboard.Store:HandleMessage("CAPACITY", "main", 1, "s1", "{live_cap}")')
        self.assertEqual(self.lua.eval("LifeDashboard.Store.capacity.total"), 1000)
        self.assertEqual(self.lua.eval("LifeDashboard.Store.capacity.cityActive"), 45)
        self.assertEqual(self.lua.eval("LifeDashboard.Store.capacity.cityTarget"), 120)
        self.assertEqual(self.lua.eval("LifeDashboard.Store.capacity.pvpActive"), 30)
        self.assertEqual(self.lua.eval("LifeDashboard.Store.capacity.pvpTarget"), 80)
        self.assertEqual(self.lua.eval("LifeDashboard.Store.capacity.free"), 925)

    def test_04_real_roster_parsing_and_pruning(self):
        """Verify parsing of real telemetry roster records from both modules and snapshot generation pruning."""
        self.lua.execute('LifeDashboard.Store:HandleMessage("WELCOME", "main", 1, "s1", "all|admin|0|0")')
        
        # Generation 1: 2 City bots, 2 PvP bots
        roster_gen1 = (
            "0x0000000000000001|Thoradin|city|1|80|alliance|Stormwind - Trade District|DuelRitual|Approach challenger|Duel countdown Arbiter|4500|Deadline|Active|-8912.4|541.2|93.1|Stormwind City|Gate Duelist\\n"
            "0x0000000000000002|Jaina|living-cities|8|80|alliance|Stormwind - Cathedral Square|ScriptedChat|Emote Bow|Deliver greeting dialogue|12000|Conditional|Active|-8654.1|432.8|101.4|Stormwind City|Plaza Socializer\\n"
            "0x0000000000000003|Mandokir|pvp|1|80|horde|STV_Gurubashi|Skirmish|Mortal Strike|Engage enemy Kurzen|1500|Observed|InCombat|-11910.4|460.2|3.5|Stranglethorn Vale|Gladiator\\n"
            "0x0000000000000004|Kurzen|world-conflicts|4|80|alliance|STV_Gurubashi|Skirmish|Ambush|Vanish & reset range|2000|Observed|InCombat|-11920.1|450.8|3.2|Stranglethorn Vale|Gladiator"
        )
        
        self.lua.execute(f'LifeDashboard.Store:HandleMessage("ROSTER", "main", 1, "s1", "{roster_gen1}")')
        
        # Check bot count
        bot_count = self.lua.eval("#LifeDashboard.Store.botList")
        self.assertEqual(bot_count, 4, "Should have parsed 4 bots across both modules")
        
        # Verify Thoradin
        thoradin_mod = self.lua.eval('LifeDashboard.Store.bots["0x0000000000000001"].module')
        self.assertEqual(thoradin_mod, "city")
        thoradin_role = self.lua.eval('LifeDashboard.Store.bots["0x0000000000000001"].role')
        self.assertEqual(thoradin_role, "Gate Duelist")
        thoradin_x = self.lua.eval('LifeDashboard.Store.bots["0x0000000000000001"].coords.x')
        self.assertAlmostEqual(thoradin_x, -8912.4, places=1)
        
        # Verify Jaina with alias 'living-cities' normalized to 'city'
        jaina_mod = self.lua.eval('LifeDashboard.Store.bots["0x0000000000000002"].module')
        self.assertEqual(jaina_mod, "city")
        
        # Verify Kurzen with alias 'world-conflicts' normalized to 'pvp'
        kurzen_mod = self.lua.eval('LifeDashboard.Store.bots["0x0000000000000004"].module')
        self.assertEqual(kurzen_mod, "pvp")
        
        # Generation 2: Thoradin and Mandokir departed; only Jaina and Kurzen remain
        roster_gen2 = (
            "0x0000000000000002|Jaina|city|8|80|alliance|Stormwind - Cathedral Square|ScriptedChat|Emote Bow|Deliver greeting dialogue|8000|Conditional|Active|-8654.1|432.8|101.4|Stormwind City|Plaza Socializer\\n"
            "0x0000000000000004|Kurzen|pvp|4|80|alliance|STV_Gurubashi|Skirmish|Eviscerate|Maintain tactical range|1200|Observed|InCombat|-11922.0|452.1|3.2|Stranglethorn Vale|Gladiator"
        )
        self.lua.execute(f'LifeDashboard.Store:HandleMessage("ROSTER", "main", 2, "s1", "{roster_gen2}")')
        
        bot_count_gen2 = self.lua.eval("#LifeDashboard.Store.botList")
        self.assertEqual(bot_count_gen2, 2, "Departed bots must be pruned upon receiving new snapshot generation")
        self.assertTrue(self.lua.eval('LifeDashboard.Store.bots["0x0000000000000001"] == nil'))
        self.assertTrue(self.lua.eval('LifeDashboard.Store.bots["0x0000000000000003"] == nil'))
        self.assertTrue(self.lua.eval('LifeDashboard.Store.bots["0x0000000000000002"] ~= nil'))
        self.assertTrue(self.lua.eval('LifeDashboard.Store.bots["0x0000000000000004"] ~= nil'))
        
        # Generation 3: Empty snapshot (all bots despawned)
        self.lua.execute('LifeDashboard.Store:HandleMessage("ROSTER", "main", 3, "s1", "")')
        bot_count_gen3 = self.lua.eval("#LifeDashboard.Store.botList")
        self.assertEqual(bot_count_gen3, 0, "Empty snapshot must prune all server-authoritative bots")

    def test_05_hubs_zones_queues_parsing(self):
        """Verify real server format parsing for HUBS, ZONES, and QUEUES."""
        self.lua.execute('LifeDashboard.Store:HandleMessage("WELCOME", "main", 1, "s1", "all|admin|0|0")')
        
        # HUBS: hubId|name|target|active|pending|poiCount|timeMult
        hubs_payload = (
            "1|Stormwind|35|12|2|14|1.0\\n"
            "2|Orgrimmar|35|10|1|14|1.0\\n"
            "8|Dalaran|25|6|0|12|1.0"
        )
        self.lua.execute(f'LifeDashboard.Store:HandleMessage("HUBS", "main", 1, "s1", "{hubs_payload}")')
        hub_count = self.lua.eval("#LifeDashboard.Store.cityHubList")
        self.assertEqual(hub_count, 3)
        sw_name = self.lua.eval('LifeDashboard.Store.cityHubList[1].name')
        self.assertEqual(sw_name, "Stormwind")
        sw_active = self.lua.eval('LifeDashboard.Store.cityHubList[1].active')
        self.assertEqual(sw_active, 12)
        
        # ZONES: zoneId|name|actType|minL|maxL|aAll|aHorde|cd
        zones_payload = (
            "1|STV_Gurubashi|Skirmish|35|80|4|4|0\\n"
            "5|Wintergrasp|Skirmish|75|80|0|0|180"
        )
        self.lua.execute(f'LifeDashboard.Store:HandleMessage("ZONES", "main", 1, "s1", "{zones_payload}")')
        zone_count = self.lua.eval("#LifeDashboard.Store.pvpZoneList")
        self.assertEqual(zone_count, 2)
        wg_cd = self.lua.eval('LifeDashboard.Store.pvpZoneList[2].cooldownSec')
        self.assertEqual(wg_cd, 180)
        
        # QUEUES: taskId|queue|botName|taskType|dueMs|truthClass
        queues_payload = (
            "1|move|Thoradin|Move to Objective|3500|Queued\\n"
            "2|duel|Varian|Duel Garrosh|1200|Deadline"
        )
        self.lua.execute(f'LifeDashboard.Store:HandleMessage("QUEUES", "main", 1, "s1", "{queues_payload}")')
        queue_count = self.lua.eval("#LifeDashboard.Store.workQueues")
        self.assertEqual(queue_count, 2)
        q1_type = self.lua.eval('LifeDashboard.Store.workQueues[1].taskType')
        self.assertEqual(q1_type, "Move to Objective")

    def test_06_query_bot_detail(self):
        """Verify QUERY_BOT outbound request and BOT_DETAIL response caching."""
        self.lua.execute('LifeDashboard.Store:HandleMessage("WELCOME", "main", 1, "s1", "all|admin|0|0")')
        
        # Seed 1 bot in roster
        bot_rec = "0x0000000000000009|Arthas|city|2|80|alliance|Stormwind|PatrolWalls|MovePoint Leg 1|Patrol gate|5000|Deadline|Active"
        self.lua.execute(f'LifeDashboard.Store:HandleMessage("ROSTER", "main", 1, "s1", "{bot_rec}")')
        
        # Bot detail response: guid|role|action|targetName|targetHp|spellName|strategies|lastAction
        detail_payload = "0x0000000000000009|Wall Patroller|MovePoint 2|TargetDummy|85|Holy Light|+dps,+stay|MovePoint Leg 1"
        self.lua.execute(f'LifeDashboard.Store:HandleMessage("BOT_DETAIL", "main", 1, "s1", "{detail_payload}")')
        
        detail_target = self.lua.eval('LifeDashboard.Store.bots["0x0000000000000009"].detail.targetName')
        self.assertEqual(detail_target, "TargetDummy")
        detail_hp = self.lua.eval('LifeDashboard.Store.bots["0x0000000000000009"].detail.targetHp')
        self.assertEqual(detail_hp, 85)
        detail_spell = self.lua.eval('LifeDashboard.Store.bots["0x0000000000000009"].detail.spellName')
        self.assertEqual(detail_spell, "Holy Light")

    def test_07_denied_and_corrupt_packet_handling(self):
        """Verify DENIED message alert insertion and corrupt packet rejection."""
        self.lua.execute('LifeDashboard.Store:HandleMessage("WELCOME", "main", 1, "s1", "all|admin|0|0")')
        
        # DENIED
        self.lua.execute('LifeDashboard.Store:HandleMessage("DENIED", "main", 1, "s1", "Security clearance insufficient")')
        alert_count = self.lua.eval("#LifeDashboard.Store.alerts")
        self.assertGreater(alert_count, 0)
        alert_sev = self.lua.eval('LifeDashboard.Store.alerts[1].severity')
        self.assertEqual(alert_sev, "WARN")
        self.assertIn("Security clearance insufficient", self.lua.eval('LifeDashboard.Store.alerts[1].text'))
        
        # Malformed packet received on wire: bad CRC
        # Wire grammar: V|kind|session|stream|seq|request|part|parts|bytes|crc|body
        bad_crc_frame = "1|CAPACITY|s1|main|1|50|1|1|10|DEADBEEF|100|10|10|0|0|10|10|0|0|80"
        self.lua.execute(f'LifeDashboard.Protocol:OnPacketReceived("{bad_crc_frame}", "AdminPlayer", "WHISPER")')
        
        # Should not update capacity due to CRC failure
        self.assertNotEqual(self.lua.eval("LifeDashboard.Store.capacity.total"), 100)

    def test_08_overview_cards_and_module_filtering(self):
        """Verify Overview card updates with real vs empty capacity, and filtering with module aliases."""
        self.lua.execute('LifeDashboard.Store:HandleMessage("WELCOME", "main", 1, "s1", "all|admin|0|0")')

        # Setup mock OverviewPane
        self.lua.execute("""
            LifeDashboard.OverviewPane = {
                CardTotal = { Value = { SetText = function(s, v) s.val = v end }, Subtext = { SetText = function(s, v) s.sub = v end } },
                CardCity = { Value = { SetText = function(s, v) s.val = v end }, Subtext = { SetText = function(s, v) s.sub = v end } },
                CardPvP = { Value = { SetText = function(s, v) s.val = v end }, Subtext = { SetText = function(s, v) s.sub = v end } },
                CardFree = { Value = { SetText = function(s, v) s.val = v end }, Subtext = { SetText = function(s, v) s.sub = v end } },
                SearchBox = { GetText = function() return "" end },
                Table = { SetData = function(s, data) s.data = data end, data = {} },
                selectedModuleFilter = "ALL"
            }
        """)

        # Zero capacity received
        self.lua.execute('LifeDashboard.Store:HandleMessage("CAPACITY", "main", 1, "s1", "0|0|0|0|0|0|0|0|0|0")')
        self.lua.execute("LifeDashboard.Overview:UpdateCards()")

        card_total = self.lua.eval("LifeDashboard.OverviewPane.CardTotal.Value.val")
        self.assertEqual(card_total, "0", "Card total should show real 0, not fake 500")

        card_city = self.lua.eval("LifeDashboard.OverviewPane.CardCity.Value.val")
        self.assertEqual(card_city, "0 / 0", "Card city should show real 0 / 0, not fake 19 / 175")

        # Seed bots with canonical and alias module names
        roster_payload = (
            "0x101|CityBot1|city|1|80|alliance|Stormwind|Patrol|Action|Task|1000|Deadline|Active\\n"
            "0x102|CityBot2|living-cities|2|80|alliance|Ironforge|Shop|Action|Task|2000|Deadline|Active\\n"
            "0x201|PvPBot1|pvp|4|80|horde|Gurubashi|Skirmish|Action|Task|1500|Observed|Active\\n"
            "0x202|PvPBot2|world-conflicts|5|80|horde|Wintergrasp|Skirmish|Action|Task|1800|Observed|Active"
        )
        self.lua.execute(f'LifeDashboard.Store:HandleMessage("ROSTER", "main", 1, "s1", "{roster_payload}")')

        # Test filter: ALL
        self.lua.execute("""
            LifeDashboard.OverviewPane.selectedModuleFilter = "ALL"
            LifeDashboard.Overview:ApplyFilters()
        """)
        count_all = self.lua.eval("#LifeDashboard.OverviewPane.Table.data")
        self.assertEqual(count_all, 4)

        # Test filter: city (should match both 'city' and 'living-cities')
        self.lua.execute("""
            LifeDashboard.OverviewPane.selectedModuleFilter = "city"
            LifeDashboard.Overview:ApplyFilters()
        """)
        count_city = self.lua.eval("#LifeDashboard.OverviewPane.Table.data")
        self.assertEqual(count_city, 2, "Module filter 'city' must match both 'city' and 'living-cities'")

        # Test filter: pvp (should match both 'pvp' and 'world-conflicts')
        self.lua.execute("""
            LifeDashboard.OverviewPane.selectedModuleFilter = "pvp"
            LifeDashboard.Overview:ApplyFilters()
        """)
        count_pvp = self.lua.eval("#LifeDashboard.OverviewPane.Table.data")
        self.assertEqual(count_pvp, 2, "Module filter 'pvp' must match both 'pvp' and 'world-conflicts'")

    def test_09_city_and_pvp_panes_filtering(self):
        """Verify CityLife and PvPLife panes resident and participant filtering with hub and zone selection."""
        self.lua.execute('LifeDashboard.Store:HandleMessage("WELCOME", "main", 1, "s1", "all|admin|0|0")')

        # Setup mock CityLifePane and PvPLifePane
        self.lua.execute("""
            LifeDashboard.CityLifePane = {
                HubTitle = { SetText = function(s, v) s.txt = v end },
                ResTitle = { SetText = function(s, v) s.txt = v end },
                HubTable = { SetData = function(s, d) s.data = d end, data = {} },
                ResTable = { SetData = function(s, d) s.data = d end, data = {} },
            }
            LifeDashboard.PvPLifePane = {
                ZoneTitle = { SetText = function(s, v) s.txt = v end },
                PartTitle = { SetText = function(s, v) s.txt = v end },
                QueueTitle = { SetText = function(s, v) s.txt = v end },
                ZoneTable = { SetData = function(s, d) s.data = d end, data = {} },
                PartTable = { SetData = function(s, d) s.data = d end, data = {} },
                QueueTable = { SetData = function(s, d) s.data = d end, data = {} },
            }
        """)

        # Seed data
        roster_payload = (
            "0x101|StormwindGuard|city|1|80|alliance|Stormwind - Trade|Patrol|Act|Task|1000|Deadline|Active|-8900|500|90|Stormwind City|Guard\\n"
            "0x102|IronforgeMiner|city|1|80|alliance|Ironforge - Forge|Work|Act|Task|1000|Deadline|Active|-4900|-900|500|Ironforge|Miner\\n"
            "0x201|ArenaChamp|pvp|1|80|horde|STV_Gurubashi|Skirmish|Act|Task|1000|Observed|Active|-11900|400|3|STV_Gurubashi|Gladiator"
        )
        self.lua.execute(f'LifeDashboard.Store:HandleMessage("ROSTER", "main", 1, "s1", "{roster_payload}")')

        # CityLife: all residents
        self.lua.execute("""
            LifeDashboard.CityLife.selectedHub = nil
            LifeDashboard.CityLife:UpdateResidents()
        """)
        city_all = self.lua.eval("#LifeDashboard.CityLifePane.ResTable.data")
        self.assertEqual(city_all, 2)

        # CityLife: select Stormwind
        self.lua.execute("""
            LifeDashboard.CityLife:SelectHub("Stormwind")
        """)
        city_sw = self.lua.eval("#LifeDashboard.CityLifePane.ResTable.data")
        self.assertEqual(city_sw, 1)
        self.assertEqual(self.lua.eval("LifeDashboard.CityLifePane.ResTable.data[1].name"), "StormwindGuard")

        # PvPLife: all participants
        self.lua.execute("""
            LifeDashboard.PvPLife.selectedZone = nil
            LifeDashboard.PvPLife:UpdateParticipants()
        """)
        pvp_all = self.lua.eval("#LifeDashboard.PvPLifePane.PartTable.data")
        self.assertEqual(pvp_all, 1)

    def test_10_opt_in_mock_demo_mode(self):
        """Verify Store:InjectMockData populates demo state only when explicitly invoked."""
        self.lua.execute("LifeDashboard.Store:InitWorld()")
        self.assertFalse(self.lua.eval("LifeDashboard.Store.isMockData"))
        self.assertEqual(self.lua.eval("#LifeDashboard.Store.botList"), 0)

        # Explicit opt-in demonstration injection
        self.lua.execute("LifeDashboard.Store:InjectMockData()")
        self.assertTrue(self.lua.eval("LifeDashboard.Store.isMockData"))
        self.assertTrue(self.lua.eval("LifeDashboard.Store.hasServerCapacity"))
        self.assertGreater(self.lua.eval("#LifeDashboard.Store.botList"), 0)
        self.assertGreater(self.lua.eval("#LifeDashboard.Store.cityHubList"), 0)

        # Reset world returns to clean state
        self.lua.execute("LifeDashboard.Store:ResetWorld()")
        self.assertFalse(self.lua.eval("LifeDashboard.Store.isMockData"))
        self.assertFalse(self.lua.eval("LifeDashboard.Store.hasServerCapacity"))
        self.assertEqual(self.lua.eval("#LifeDashboard.Store.botList"), 0)

    def test_all_toc_lua_loads_under_luajit(self):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "addon", "CitiesConflictsDashboard"))
        toc = os.path.join(base_dir, "CitiesConflictsDashboard.toc")
        parse = self.lua.eval("function(code, name) assert(loadstring(code, name)) end")
        with open(toc, encoding="utf-8") as toc_file:
            for entry in toc_file:
                entry = entry.strip()
                if entry.endswith(".lua"):
                    with self.subTest(file=entry), open(os.path.join(base_dir, *entry.split("\\")), encoding="utf-8") as source:
                        parse(source.read(), entry)

    def test_unsigned_crc_matches_server_frames(self):
        """LuaJIT bit operations are signed. Wire CRC is exactly eight hex digits."""
        self.assertEqual(self.lua.eval('LifeDashboard.Protocol:CalculateCRC32("123456789")'), "CBF43926")

    def test_paged_roster_waits_for_complete_snapshot_and_tracks_changes(self):
        """Feed real Lua paged wire fragments with independently generated CRCs."""
        self.lua.execute('LifeDashboard.Store:HandleMessage("WELCOME", "main", 1, "1", "all|admin|0|0")')
        row = "0x101|CityBot|city|1|80|alliance|Stormwind|Native RPG|{}|Native AI decides|0|Observed|Resident"
        other = "0x102|DuelBot|pvp|1|80|horde|Orgrimmar|Duel|Staging|Reach staging point|0|Observed|Staging"
        protocol = self.lua.globals().LifeDashboard.Protocol

        def frame(kind, stream, snapshot, body):
            raw = body.encode("ascii")
            encoded = "".join(f"%{byte:02X}" if byte in (37, 124) or byte < 32 else chr(byte) for byte in raw)
            chunks = [encoded[offset:offset + 100] for offset in range(0, len(encoded), 100)]
            return [
                f"1|{kind}|1|{stream}|1|{snapshot}|{part}|{len(chunks)}|{len(raw)}|{zlib.crc32(raw):08X}|{chunk}"
                for part, chunk in enumerate(chunks, 1)
            ]

        first = frame("ROSTER_PAGE", "roster-1", 8, "1|2\n" + row.format("sell") + "\n")
        second = frame("ROSTER_PAGE", "roster-2", 8, "2|2\n" + other + "\n")
        protocol.OnPacketReceived(protocol, second[0], "AdminPlayer", "WHISPER")
        for packet in first:
            protocol.OnPacketReceived(protocol, packet, "AdminPlayer", "WHISPER")
        self.assertEqual(self.lua.eval("#LifeDashboard.Store.botList"), 0)
        for packet in second[1:]:
            protocol.OnPacketReceived(protocol, packet, "AdminPlayer", "WHISPER")
        self.assertEqual(self.lua.eval("#LifeDashboard.Store.botList"), 2)

        # A new complete generation prunes the second bot and records the new action.
        for packet in frame("ROSTER_PAGE", "roster-1", 9, "1|1\n" + row.format("repair") + "\n"):
            protocol.OnPacketReceived(protocol, packet, "AdminPlayer", "WHISPER")
        self.assertEqual(self.lua.eval("#LifeDashboard.Store.botList"), 1)
        self.assertEqual(self.lua.eval('LifeDashboard.Store.bots["0x101"].actionHistory[1].action'), "repair")
        self.assertEqual(self.lua.eval('LifeDashboard.Store.bots["0x101"].actionHistory[2].action'), "sell")
        for packet in second:
            protocol.OnPacketReceived(protocol, packet, "AdminPlayer", "WHISPER")
        self.assertEqual(self.lua.eval("#LifeDashboard.Store.botList"), 1)

    def test_virtualized_table_scrolls_under_rows_and_with_keyboard(self):
        self.lua.execute("""
            local realCreateFrame = CreateFrame
            local methods = {
                SetScript = function(self, event, handler) self[event] = handler end,
                SetMinMaxValues = function(self, low, high) self.low, self.high = low, high end,
                GetValue = function(self) return self.value or 0 end,
                SetValue = function(self, value)
                    self.value = math.max(self.low, math.min(self.high, value))
                    if self.OnValueChanged then self:OnValueChanged(self.value) end
                end,
                EnableMouseWheel = function(self, enabled) self.wheelEnabled = enabled end,
                EnableKeyboard = function(self, enabled) self.keyboardEnabled = enabled end,
                Show = function(self) self.visible = true end,
                Hide = function(self) self.visible = false end,
                CreateFontString = function(self) return self end,
                CreateTexture = function(self) return self end,
            }
            CreateFrame = function()
                return setmetatable({}, {__index = function(_, key) return methods[key] or function() end end})
            end
            local hovered = true
            MouseIsOver = function() return hovered end
            GetCurrentKeyBoardFocus = function() return nil end
            local view = LifeDashboard.Widgets:CreateVirtualizedTable(nil, 200, 80, 24,
                {{name = "Bot", width = 90}}, function(row, value) row.valueBound = value end)
            view:SetData({1, 2, 3, 4, 5, 6})
            assert(view.Rows[1].wheelEnabled)
            view.Rows[1]:OnMouseWheel(-1)
            assert(view.Rows[1].valueBound == 4)
            view.ScrollUp:OnClick()
            assert(view.Rows[1].valueBound == 3)
            view:OnUpdate()
            assert(view.keyboardEnabled)
            view:OnKeyDown("DOWN")
            assert(view.Rows[1].valueBound == 4)
            view:OnKeyDown("END")
            assert(view.Rows[1].valueBound == 5)
            view:SetData({1, 2, 3})
            assert(view.Rows[1].valueBound == 2)
            hovered = false
            view:OnUpdate()
            assert(not view.keyboardEnabled)
            CreateFrame = realCreateFrame
            GetCurrentKeyBoardFocus = nil
            MouseIsOver = nil
        """)

if __name__ == "__main__":
    unittest.main()
