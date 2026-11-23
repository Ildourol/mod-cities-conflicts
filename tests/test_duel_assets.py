"""Read the shipped seeds and, when present, the extracted AzerothCore client data."""

import csv
import math
import os
from pathlib import Path
import re
import struct
import unittest


MODULE = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get(
    "AZEROTHCORE_DATA_DIR", MODULE.parent.parent / "Azerothcore server" / "Server" / "bin"
))
DEFAULT_ZONES = {"StormwindDuel": (0, 0, 12), "OrgrimmarDuel": (1, 1, 14)}


def read_duel_seeds(path):
    rows = re.findall(r"^\(([^\n]+)\)[,;]$", path.read_text(encoding="utf8"), re.MULTILINE)
    return {
        row[0]: row
        for row in csv.reader(rows, quotechar="'", skipinitialspace=True)
        if row[0] in DEFAULT_ZONES
    }


def dbc(path):
    data = path.read_bytes()
    magic, count, fields, stride, _ = struct.unpack_from("<4s4I", data)
    if magic != b"WDBC" or fields * 4 != stride:
        raise ValueError(f"Unsupported DBC layout in {path}")
    return {
        row[0]: row
        for row in struct.iter_unpack(f"<{fields}I", data[20:20 + count * stride])
    }


def grid_area(map_id, x, y):
    # GridTerrainLoader::LoadMap and GridTerrainData::getArea, map format version 9.
    gx, gy = 32 - x / (1600 / 3), 32 - y / (1600 / 3)
    tile = f"{map_id:03}{int(gx):02}{int(gy):02}"
    data = (DATA / "maps" / f"{tile}.map").read_bytes()
    magic, version, _, area_offset = struct.unpack_from("<4s3I", data)
    if magic != b"MAPS" or version != 9:
        raise ValueError(f"Unsupported map format in {tile}")
    magic, flags, area = struct.unpack_from("<4sHH", data, area_offset)
    if magic != b"AREA":
        raise ValueError(f"Missing area data in {tile}")
    if not flags & 1:
        index = (int(gx * 16) & 15) * 16 + (int(gy * 16) & 15)
        area = struct.unpack_from("<H", data, area_offset + 8 + 2 * index)[0]
    return area


class DuelAssetsTest(unittest.TestCase):
    def setUp(self):
        self.updates = read_duel_seeds(
            MODULE / "data/sql/world/updates/2026_10_11_02_world_pvp_life_seed_idempotency.sql"
        )

    def test_manual_and_update_duel_seeds_agree(self):
        manual = read_duel_seeds(MODULE / "data/sql/manual/world_pvp_life.sql")
        self.assertEqual(self.updates, manual)
        self.assertEqual(self.updates.keys(), DEFAULT_ZONES.keys())
        for name, (map_id, team, _) in DEFAULT_ZONES.items():
            with self.subTest(zone=name):
                enabled, kind, attacker, defender, minimum, maximum, map_column = map(int, self.updates[name][1:8])
                self.assertEqual((enabled, kind, attacker, defender, map_column), (1, 1, team, team, map_id))
                self.assertTrue(1 <= minimum <= maximum <= 80)
                self.assertTrue(all(math.isfinite(float(value)) for value in self.updates[name][8:12]))

    @unittest.skipUnless((DATA / "maps").is_dir() and (DATA / "dbc").is_dir(), "extracted client data unavailable")
    def test_seed_anchors_have_outdoor_duel_areas(self):
        areas = dbc(DATA / "dbc/AreaTable.dbc")
        for name, (map_id, _, zone) in DEFAULT_ZONES.items():
            with self.subTest(zone=name):
                x, y = map(float, self.updates[name][8:10])
                area = areas[grid_area(map_id, x, y)]
                self.assertEqual(area[1], map_id)
                self.assertEqual(area[2] or area[0], zone)
                self.assertTrue(area[4] & 0x40)  # AREA_FLAG_ALLOW_DUELS

    @unittest.skipUnless((DATA / "dbc").is_dir(), "extracted client data unavailable")
    def test_configured_duel_spell_supports_the_close_approach_distance(self):
        config = (MODULE / "conf/mod_cities_conflicts.conf.dist").read_text(encoding="utf8")
        spell_id = int(re.search(r"^PvPLife\.Duel\.SpellId\s*=\s*(\d+)", config, re.MULTILINE)[1])
        spell = dbc(DATA / "dbc/Spell.dbc")[spell_id]
        spell_range = dbc(DATA / "dbc/SpellRange.dbc")[spell[46]]
        hostile, friendly = struct.unpack("<2f", struct.pack("<2I", *spell_range[3:5]))
        self.assertGreaterEqual(min(hostile, friendly), 5.0)


if __name__ == "__main__":
    unittest.main()
