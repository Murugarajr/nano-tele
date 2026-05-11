import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, datetime
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "workspace" / "tools" / "perfume_tool.py"
SPEC = importlib.util.spec_from_file_location("perfume_tool", MODULE_PATH)
perfume_tool = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["perfume_tool"] = perfume_tool
SPEC.loader.exec_module(perfume_tool)


class PerfumeToolTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp.name)
        self.data = self.workspace / "data"
        self.memory = self.workspace / "memory"
        self.data.mkdir()
        self.memory.mkdir()

        perfume_tool.WORKSPACE = self.workspace
        perfume_tool.DATA_DIR = self.data
        perfume_tool.MEMORY_DIR = self.memory
        perfume_tool.FRAGRANCES_PATH = self.data / "fragrances.json"
        perfume_tool.RANKING_PATH = self.data / "ranking.json"
        perfume_tool.PREFERENCES_PATH = self.data / "preferences.json"
        perfume_tool.RECENT_PICKS_PATH = self.memory / "RECENT_PICKS.md"
        perfume_tool.FEEDBACK_PATH = self.memory / "FEEDBACK.md"

        fragrances = [
            {
                "name": "Imagination",
                "brand": "Louis Vuitton",
                "family": "Citrus Aromatic",
                "best_weather": ["Mild", "Cool & dry"],
                "best_occasion": ["Daytime", "Office"],
                "summary": "clean citrus",
            },
            {
                "name": "Sauvage",
                "brand": "Dior",
                "family": "Woody Fresh",
                "best_weather": ["Mild", "Cool & dry"],
                "best_occasion": ["Daytime", "Office"],
                "summary": "woody fresh",
            },
            {
                "name": "Born in Roma Uomo",
                "brand": "Valentino",
                "family": "Aromatic Woody",
                "best_weather": ["Mild"],
                "best_occasion": ["Office"],
                "summary": "aromatic woods",
            },
        ]
        rankings = {
            "Mild": {
                "Daytime": ["Imagination", "Sauvage", "Born in Roma Uomo"],
                "Office": ["Imagination", "Born in Roma Uomo", "Sauvage"],
            },
            "Cool & dry": {"Daytime": ["Imagination", "Sauvage"]},
        }
        perfume_tool.write_json(perfume_tool.FRAGRANCES_PATH, fragrances)
        perfume_tool.write_json(perfume_tool.RANKING_PATH, rankings)
        perfume_tool.write_json(perfume_tool.PREFERENCES_PATH, {"temporary_city": None, "feedback": {}})
        perfume_tool.RECENT_PICKS_PATH.write_text(
            "# Recent\n\n| Date | City | Weather Bucket | Occasion | Perfume |\n"
            "|------|------|----------------|----------|---------|\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_classifies_weather_boundaries(self):
        self.assertEqual(perfume_tool.classify_weather(27, 40), "Hot & dry")
        self.assertEqual(perfume_tool.classify_weather(27, 70), "Hot & humid")
        self.assertEqual(perfume_tool.classify_weather(15, 90), "Mild")
        self.assertEqual(perfume_tool.classify_weather(12, 50), "Cool & dry")
        self.assertEqual(perfume_tool.classify_weather(12, 80), "Cold & rainy")
        self.assertEqual(perfume_tool.classify_weather(5, 50), "Cold & dry")

    def test_infers_occasion_from_request_and_time(self):
        self.assertEqual(perfume_tool.infer_occasion("big meeting"), "Office")
        self.assertEqual(perfume_tool.infer_occasion("date night"), "Date")
        self.assertEqual(perfume_tool.infer_occasion(now=datetime(2026, 5, 2, 10)), "Daytime")
        self.assertEqual(perfume_tool.infer_occasion(now=datetime(2026, 5, 2, 20)), "Evening")

    def test_extracts_city_from_natural_recommendation_text(self):
        self.assertEqual(perfume_tool.extract_city("What should I wear in London today?"), "London")
        self.assertEqual(perfume_tool.extract_city("What should I wear London today?"), "London")
        self.assertEqual(perfume_tool.extract_city("/today Manchester"), "Manchester")
        self.assertEqual(perfume_tool.extract_city("today Manchester"), "Manchester")
        self.assertEqual(perfume_tool.extract_city("office@perfume_bot London"), "London")

    def test_routes_occasion_from_natural_text(self):
        self.assertEqual(perfume_tool.route_occasion("What should I wear in London today?"), "today")
        self.assertEqual(perfume_tool.route_occasion("/evening Manchester"), "evening")
        self.assertEqual(perfume_tool.route_occasion("evening Manchester"), "evening")
        self.assertEqual(perfume_tool.route_occasion("/today@perfume_bot"), "today")
        self.assertEqual(perfume_tool.route_occasion("today@perfume_bot"), "today")
        self.assertEqual(perfume_tool.route_occasion("Need something for date night"), "date")

    def test_rotation_blocks_yesterdays_global_pick(self):
        yesterday = date(2026, 5, 1)
        perfume_tool.RECENT_PICKS_PATH.write_text(
            "# Recent\n\n| Date | City | Weather Bucket | Occasion | Perfume |\n"
            "|------|------|----------------|----------|---------|\n"
            f"| {yesterday.isoformat()} | Manchester, GB | Mild | Daytime | Imagination |\n",
            encoding="utf-8",
        )
        selected = perfume_tool.choose_perfume("Mild", "Daytime", "Sheffield, GB", today=date(2026, 5, 2))
        self.assertEqual(selected["name"], "Sauvage")

    def test_feedback_can_promote_candidate_when_not_blocked(self):
        perfume_tool.write_json(
            perfume_tool.PREFERENCES_PATH,
            {"temporary_city": None, "feedback": {"Sauvage": 3, "Imagination": 0}},
        )
        selected = perfume_tool.choose_perfume("Mild", "Daytime", "Sheffield, GB", today=date(2026, 5, 2))
        self.assertEqual(selected["name"], "Sauvage")

    def test_appends_recent_pick(self):
        weather = perfume_tool.Weather("Sheffield, GB", 18, 55, "partly cloudy")
        perfume = perfume_tool.fragrance_by_name("Imagination")
        pick = perfume_tool.Pick(weather, "Mild", "Daytime", perfume, "clean citrus")
        perfume_tool.append_recent_pick(pick, today=date(2026, 5, 2))
        rows = perfume_tool.parse_recent_rows()
        self.assertEqual(rows[-1]["perfume"], "Imagination")
        self.assertEqual(rows[-1]["city"], "Sheffield, GB")

    def test_travel_mode_sets_active_city(self):
        args = type("Args", (), {"city": "Dubai", "clear": False})()
        with redirect_stdout(io.StringIO()):
            perfume_tool.command_travel(args)
        self.assertEqual(perfume_tool.active_city(), "Dubai")

    def test_collection_add_persists_new_fragrance(self):
        args = type(
            "Args",
            (),
            {
                "action": "add",
                "name": "Test Scent",
                "brand": "House",
                "family": "Fresh",
                "weather": "Mild, Hot & dry",
                "occasions": "Daytime",
                "summary": "fresh test",
            },
        )()
        with redirect_stdout(io.StringIO()):
            result = perfume_tool.command_collection(args)
        self.assertEqual(result, 0)
        names = [item["name"] for item in json.loads(perfume_tool.FRAGRANCES_PATH.read_text())]
        self.assertIn("Test Scent", names)


if __name__ == "__main__":
    unittest.main()
