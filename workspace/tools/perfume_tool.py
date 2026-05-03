#!/usr/bin/env python3
"""Deterministic fragrance concierge tool for the Nanobot workspace."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:  # pragma: no cover - fallback for minimal environments
    requests = None


WORKSPACE = Path(__file__).resolve().parents[1]
DATA_DIR = WORKSPACE / "data"
MEMORY_DIR = WORKSPACE / "memory"
FRAGRANCES_PATH = DATA_DIR / "fragrances.json"
RANKING_PATH = DATA_DIR / "ranking.json"
PREFERENCES_PATH = DATA_DIR / "preferences.json"
RECENT_PICKS_PATH = MEMORY_DIR / "RECENT_PICKS.md"
FEEDBACK_PATH = MEMORY_DIR / "FEEDBACK.md"
DEFAULT_CITY = "Sheffield, UK"

WEATHER_CODES = {
    0: "clear",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "fog",
    51: "light drizzle",
    53: "drizzle",
    55: "heavy drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    80: "rain showers",
    81: "rain showers",
    82: "heavy rain showers",
    95: "thunderstorm",
}

SIMILAR_FAMILIES = [
    {"Citrus Aquatic", "Citrus Fruity Oriental", "Citrus Aromatic"},
    {"Woody Fresh", "Aromatic Woody", "Aquatic Woody", "Oriental Woody", "Fruity Woody", "Amber Woody Vetiver"},
    {"Amber Gourmand", "Oriental Gourmand"},
    {"Fresh Aquatic", "Marine Aromatic"},
]


@dataclass(frozen=True)
class Weather:
    city: str
    temp_c: float
    humidity: int
    description: str
    wind_kmh: float | None = None
    high_c: float | None = None
    rain_chance: int | None = None
    estimated: bool = False


@dataclass(frozen=True)
class Pick:
    weather: Weather
    bucket: str
    occasion: str
    perfume: dict[str, Any]
    reason: str


def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_fragrances() -> list[dict[str, Any]]:
    return load_json(FRAGRANCES_PATH, [])


def load_rankings() -> dict[str, dict[str, list[str]]]:
    return load_json(RANKING_PATH, {})


def fragrance_by_name(name: str) -> dict[str, Any] | None:
    normalized = name.casefold()
    for fragrance in load_fragrances():
        if fragrance["name"].casefold() == normalized:
            return fragrance
    return None


def classify_weather(temp_c: float, humidity: int) -> str:
    if temp_c > 25 and humidity < 50:
        return "Hot & dry"
    if temp_c > 25 and humidity >= 50:
        return "Hot & humid"
    if 15 <= temp_c <= 25:
        return "Mild"
    if temp_c < 15 and humidity >= 60:
        return "Cold & rainy"
    if 10 <= temp_c < 15:
        return "Cool & dry"
    return "Cold & dry"


def infer_occasion(text: str = "", requested: str | None = None, now: datetime | None = None) -> str:
    if requested:
        normalized = requested.strip().lower()
        if normalized in {"office", "work", "meeting"}:
            return "Office"
        if normalized in {"date", "date night"}:
            return "Date"
        if normalized in {"evening", "dinner", "party", "night", "night out"}:
            return "Evening"
        if normalized in {"today", "day", "daytime", "casual"}:
            return "Daytime"

    lowered = text.lower()
    if any(word in lowered for word in ("office", "work", "meeting")):
        return "Office"
    if any(word in lowered for word in ("date", "date night")):
        return "Date"
    if any(word in lowered for word in ("evening", "dinner", "party", "night out", "night")):
        return "Evening"

    current = now or datetime.now()
    return "Daytime" if current.hour < 17 else "Evening"


def extract_city(text: str) -> str | None:
    cleaned = text.strip()
    command_match = re.match(r"^/(?:today|office|evening|date)\s+(.+)$", cleaned, flags=re.IGNORECASE)
    if command_match:
        return tidy_city(command_match.group(1))

    patterns = [
        r"\bin\s+([a-z][a-z .'-]+?)(?:\s+(?:today|tonight|now|this morning|this evening|for\b)|[?.!]|$)",
        r"\bfor\s+([a-z][a-z .'-]+?)(?:\s+(?:today|tonight|now|this morning|this evening)|[?.!]|$)",
        r"\bwear\s+([a-z][a-z .'-]+?)(?:\s+(?:today|tonight|now|this morning|this evening)|[?.!]|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, cleaned, flags=re.IGNORECASE)
        if match:
            city = tidy_city(match.group(1))
            if city and city.casefold() not in {"today", "tonight", "now", "perfume", "fragrance", "scent"}:
                return city
    return None


def tidy_city(value: str) -> str:
    city = re.sub(r"\b(today|tonight|now|please|pls)\b", "", value, flags=re.IGNORECASE)
    city = re.sub(r"\s+", " ", city).strip(" ?.!,'\"")
    return city.title() if city else ""


def route_occasion(text: str) -> str | None:
    lowered = text.lower()
    if lowered.startswith("/office") or any(word in lowered for word in ("office", "work", "meeting")):
        return "office"
    if lowered.startswith("/date") or "date" in lowered:
        return "date"
    if lowered.startswith("/evening") or any(word in lowered for word in ("evening", "dinner", "party", "night out", "tonight")):
        return "evening"
    if lowered.startswith("/today") or any(phrase in lowered for phrase in ("what should i wear", "perfume", "fragrance", "scent", "wear")):
        return "today"
    return None


def active_city(city: str | None = None) -> str:
    if city:
        return city
    prefs = load_json(PREFERENCES_PATH, {})
    return prefs.get("temporary_city") or DEFAULT_CITY


def fetch_json(url: str, timeout: int = 12) -> Any:
    if requests is not None:
        response = requests.get(url, timeout=timeout, headers={"User-Agent": "nano-tele/1.0"})
        response.raise_for_status()
        return response.json()
    request = urllib.request.Request(url, headers={"User-Agent": "nano-tele/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def weather_description(code: int | None) -> str:
    if code is None:
        return "current conditions"
    return WEATHER_CODES.get(code, "current conditions")


def get_weather(city: str) -> Weather:
    search_name = city.split(",")[0].strip() or city
    query = urllib.parse.urlencode({"name": search_name, "count": 1, "language": "en", "format": "json"})
    geo = fetch_json(f"https://geocoding-api.open-meteo.com/v1/search?{query}")
    results = geo.get("results") or []
    if not results:
        raise RuntimeError(f"Live weather lookup failed: city not found ({city})")

    place = results[0]
    latitude = place["latitude"]
    longitude = place["longitude"]
    label_parts = [place.get("name"), place.get("admin1"), place.get("country_code")]
    label = ", ".join(part for part in label_parts if part)
    params = urllib.parse.urlencode(
        {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "daily": "temperature_2m_max,precipitation_probability_max",
            "timezone": "auto",
            "forecast_days": 1,
        }
    )
    forecast = fetch_json(f"https://api.open-meteo.com/v1/forecast?{params}")
    current = forecast.get("current") or {}
    daily = forecast.get("daily") or {}
    highs = daily.get("temperature_2m_max") or []
    rain = daily.get("precipitation_probability_max") or []
    try:
        return Weather(
            city=label or city,
            temp_c=float(current["temperature_2m"]),
            humidity=int(current["relative_humidity_2m"]),
            description=weather_description(current.get("weather_code")),
            wind_kmh=float(current["wind_speed_10m"]) if "wind_speed_10m" in current else None,
            high_c=float(highs[0]) if highs else None,
            rain_chance=int(rain[0]) if rain else None,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"Live weather lookup failed: incomplete weather response for {city}") from exc


def parse_recent_rows() -> list[dict[str, str]]:
    if not RECENT_PICKS_PATH.exists():
        return []
    rows: list[dict[str, str]] = []
    for line in RECENT_PICKS_PATH.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| ") or line.startswith("| Date") or line.startswith("|------"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 5 or not re.match(r"\d{4}-\d{2}-\d{2}", cells[0]):
            continue
        rows.append(
            {
                "date": cells[0],
                "city": cells[1],
                "bucket": cells[2],
                "occasion": cells[3],
                "perfume": cells[4],
            }
        )
    return rows


def append_recent_pick(pick: Pick, today: date | None = None) -> None:
    today = today or date.today()
    RECENT_PICKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not RECENT_PICKS_PATH.exists():
        RECENT_PICKS_PATH.write_text(
            "# Recent Perfume Recommendations Log\n\n"
            "| Date | City | Weather Bucket | Occasion | Perfume |\n"
            "|------|------|----------------|----------|---------|\n",
            encoding="utf-8",
        )
    with RECENT_PICKS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"| {today.isoformat()} | {pick.weather.city} | {pick.bucket} | {pick.occasion} | {pick.perfume['name']} |\n")


def feedback_scores() -> dict[str, int]:
    prefs = load_json(PREFERENCES_PATH, {})
    raw = prefs.get("feedback", {})
    return {name: int(score) for name, score in raw.items()}


def same_family(family: str, other_family: str) -> bool:
    return any(family in group and other_family in group for group in SIMILAR_FAMILIES)


def candidate_names(bucket: str, occasion: str) -> list[str]:
    rankings = load_rankings()
    by_bucket = rankings.get(bucket, {})
    names = list(by_bucket.get(occasion) or by_bucket.get("Daytime") or [])
    if names:
        return names
    return [item["name"] for item in load_fragrances() if bucket in item.get("best_weather", [])]


def choose_perfume(bucket: str, occasion: str, city: str, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    yesterday = (today - timedelta(days=1)).isoformat()
    recent = [row for row in parse_recent_rows() if row["date"] == yesterday]
    city_key = city.split(",")[0].strip().casefold()
    blocked = {
        row["perfume"]
        for row in recent
        if row["city"].split(",")[0].strip().casefold() == city_key and row["bucket"] == bucket
    }
    blocked.update(row["perfume"] for row in recent)

    fragrances = {item["name"]: item for item in load_fragrances()}
    names = [name for name in candidate_names(bucket, occasion) if name in fragrances]
    scores = feedback_scores()
    names.sort(key=lambda name: scores.get(name, 0), reverse=True)

    for name in names:
        if name not in blocked:
            return fragrances[name]

    skipped = [fragrances[name] for name in names if name in fragrances]
    for name in names:
        fragrance = fragrances[name]
        if any(same_family(fragrance["family"], item["family"]) for item in skipped):
            return fragrance

    fallback = next((item for item in load_fragrances() if bucket in item.get("best_weather", [])), None)
    if fallback:
        return fallback
    raise RuntimeError(f"No fragrance configured for {bucket} / {occasion}")


def build_pick(city: str | None, occasion: str | None, text: str = "", weather: Weather | None = None) -> Pick:
    resolved_city = active_city(city)
    current_weather = weather or get_weather(resolved_city)
    bucket = classify_weather(current_weather.temp_c, current_weather.humidity)
    resolved_occasion = infer_occasion(text=text, requested=occasion)
    perfume = choose_perfume(bucket, resolved_occasion, current_weather.city)
    reason = f"{perfume['summary']}, suited to {bucket.lower()} {resolved_occasion.lower()} conditions"
    if current_weather.rain_chance is not None and current_weather.rain_chance >= 60:
        reason += f" with rain risk at {current_weather.rain_chance}%"
    return Pick(current_weather, bucket, resolved_occasion, perfume, reason)


def format_pick(pick: Pick) -> str:
    weather = pick.weather
    estimated = " estimated" if weather.estimated else ""
    high = f", high {round(weather.high_c)}°C" if weather.high_c is not None else ""
    rain = f", rain {weather.rain_chance}%" if weather.rain_chance is not None else ""
    return (
        f"🌤️ *{weather.city}: {round(weather.temp_c)}°C, {weather.description}, "
        f"{weather.humidity}% humidity{high}{rain}{estimated}*\n"
        f"💨 Wear **{pick.perfume['name']} by {pick.perfume['brand']}** — {pick.reason}."
    )


def command_recommend(args: argparse.Namespace) -> int:
    try:
        pick = build_pick(args.city, args.occasion, args.text or "")
    except Exception as exc:
        city = active_city(args.city)
        print(f"Live weather is unavailable for {city} right now, so I cannot make a weather-based recommendation.")
        return 0
    print(format_pick(pick))
    append_recent_pick(pick)
    return 0


def command_route(args: argparse.Namespace) -> int:
    text = args.text.strip()
    lowered = text.lower()
    slash = re.match(r"^/([a-z]+)(?:@\w+)?(?:\s+.*)?$", lowered)
    slash_command = slash.group(1) if slash else ""
    if slash_command == "history" or lowered in {"history", "recent picks", "recent recommendations"} or "what did i wear recently" in lowered:
        return command_history(argparse.Namespace(limit=7))
    if slash_command == "stats" or lowered == "stats" or any(phrase in lowered for phrase in ("sotd stats", "most worn", "least worn")):
        return command_stats(argparse.Namespace())
    if "clear travel mode" in lowered or "back to sheffield" in lowered:
        return command_travel(argparse.Namespace(city=None, clear=True))
    travel_match = re.search(r"\b(?:i'?m|i am|use)\s+(?:in\s+)?([a-z][a-z .'-]+?)(?:\s+for\s+\d+\s+days|\s+this week|[?.!]|$)", text, flags=re.IGNORECASE)
    if travel_match and any(word in lowered for word in ("for", "this week")):
        return command_travel(argparse.Namespace(city=tidy_city(travel_match.group(1)), clear=False))
    if "show my collection" in lowered or lowered in {"collection", "/collection"}:
        return command_collection(argparse.Namespace(action="list"))

    occasion = route_occasion(text)
    if occasion:
        return command_recommend(argparse.Namespace(city=extract_city(text), occasion=occasion, text=text))

    print("Send /today, /office, /evening, /date, /history, or /stats.")
    return 0


def command_history(args: argparse.Namespace) -> int:
    rows = parse_recent_rows()[-args.limit :]
    if not rows:
        print("*No recent recommendations yet. Ask me what to wear today!*")
        return 0
    print("📜 *Recent Recommendations*")
    print("")
    for row in reversed(rows):
        print(f"• {row['date']}: **{row['perfume']}** — {row['city']} ({row['bucket']}, {row['occasion']})")
    return 0


def command_stats(_: argparse.Namespace) -> int:
    rows = parse_recent_rows()
    if not rows:
        print("*No stats yet. Ask for a recommendation first.*")
        return 0
    counts: dict[str, int] = {}
    weather_counts: dict[str, int] = {}
    for row in rows:
        counts[row["perfume"]] = counts.get(row["perfume"], 0) + 1
        weather_counts[row["bucket"]] = weather_counts.get(row["bucket"], 0) + 1
    most = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:3]
    least = sorted(counts.items(), key=lambda item: (item[1], item[0]))[:3]
    print("📊 *SOTD Stats*")
    print(f"Total picks: {len(rows)}")
    print("Most worn: " + ", ".join(f"{name} ({count})" for name, count in most))
    print("Least worn: " + ", ".join(f"{name} ({count})" for name, count in least))
    print("Weather: " + ", ".join(f"{bucket} ({count})" for bucket, count in sorted(weather_counts.items())))
    return 0


def command_feedback(args: argparse.Namespace) -> int:
    fragrance = fragrance_by_name(args.perfume)
    if not fragrance:
        print(f"I couldn't find **{args.perfume}** in your collection.")
        return 1
    signal = args.feedback.lower()
    delta = 1 if signal in {"liked", "like", "good", "lasted", "lasted well", "great"} else -1
    prefs = load_json(PREFERENCES_PATH, {"feedback": {}})
    scores = prefs.setdefault("feedback", {})
    scores[fragrance["name"]] = int(scores.get(fragrance["name"], 0)) + delta
    write_json(PREFERENCES_PATH, prefs)
    FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not FEEDBACK_PATH.exists():
        FEEDBACK_PATH.write_text("# Perfume Feedback Log\n\n| Date | Perfume | Feedback | Notes |\n|------|---------|----------|-------|\n", encoding="utf-8")
    notes = (args.notes or "").replace("|", "/")
    with FEEDBACK_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"| {date.today().isoformat()} | {fragrance['name']} | {args.feedback} | {notes} |\n")
    print(f"Logged feedback for **{fragrance['name']}**.")
    return 0


def command_travel(args: argparse.Namespace) -> int:
    prefs = load_json(PREFERENCES_PATH, {"feedback": {}})
    if args.clear:
        prefs["temporary_city"] = None
        prefs["temporary_city_set_at"] = None
        write_json(PREFERENCES_PATH, prefs)
        print(f"Travel mode cleared. Default city is {DEFAULT_CITY}.")
        return 0
    prefs["temporary_city"] = args.city
    prefs["temporary_city_set_at"] = datetime.now().isoformat(timespec="seconds")
    write_json(PREFERENCES_PATH, prefs)
    print(f"Travel mode set to **{args.city}**.")
    return 0


def command_collection(args: argparse.Namespace) -> int:
    fragrances = load_fragrances()
    if args.action == "list":
        for item in fragrances:
            print(f"• **{item['name']}** by {item['brand']} — {item['family']}")
        return 0
    if args.action == "remove":
        before = len(fragrances)
        fragrances = [item for item in fragrances if item["name"].casefold() != args.name.casefold()]
        if len(fragrances) == before:
            print(f"I couldn't find **{args.name}** in your collection.")
            return 1
        write_json(FRAGRANCES_PATH, fragrances)
        print(f"Removed **{args.name}** from your collection.")
        return 0
    if fragrance_by_name(args.name):
        print(f"**{args.name}** is already in your collection.")
        return 1
    fragrances.append(
        {
            "name": args.name,
            "brand": args.brand,
            "family": args.family,
            "best_weather": [item.strip() for item in args.weather.split(",")],
            "best_occasion": [item.strip() for item in args.occasions.split(",")],
            "summary": args.summary,
        }
    )
    write_json(FRAGRANCES_PATH, fragrances)
    print(f"Added **{args.name}** by {args.brand}.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Perfume recommendation helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    recommend = subparsers.add_parser("recommend")
    recommend.add_argument("--city")
    recommend.add_argument("--occasion", choices=["today", "daytime", "office", "evening", "date"])
    recommend.add_argument("--text", default="")
    recommend.set_defaults(func=command_recommend)

    route = subparsers.add_parser("route")
    route.add_argument("--text", required=True)
    route.set_defaults(func=command_route)

    history = subparsers.add_parser("history")
    history.add_argument("--limit", type=int, default=7)
    history.set_defaults(func=command_history)

    stats = subparsers.add_parser("stats")
    stats.set_defaults(func=command_stats)

    feedback = subparsers.add_parser("feedback")
    feedback.add_argument("perfume")
    feedback.add_argument("feedback")
    feedback.add_argument("--notes", default="")
    feedback.set_defaults(func=command_feedback)

    travel = subparsers.add_parser("travel")
    travel.add_argument("city", nargs="?")
    travel.add_argument("--clear", action="store_true")
    travel.set_defaults(func=command_travel)

    collection = subparsers.add_parser("collection")
    collection.add_argument("action", choices=["list", "add", "remove"])
    collection.add_argument("--name", required=False)
    collection.add_argument("--brand", default="")
    collection.add_argument("--family", default="Custom")
    collection.add_argument("--weather", default="Mild")
    collection.add_argument("--occasions", default="Daytime")
    collection.add_argument("--summary", default="a custom collection pick")
    collection.set_defaults(func=command_collection)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "action", None) in {"add", "remove"} and not args.name:
        parser.error("collection add/remove requires --name")
    if args.command == "travel" and not args.clear and not args.city:
        parser.error("travel requires a city or --clear")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
