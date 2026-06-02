"""Live weather forecast for a store location — Open-Meteo (free) or OpenWeather."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import httpx
import redis

from app.config import get_settings

# WMO weather code → short label
WMO_LABELS: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Snow",
    75: "Heavy snow",
    80: "Rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Thunderstorm with heavy hail",
}

RAIN_CODES = {51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99}
HEAT_THRESHOLD_C = 33


def _wmo_label(code: int | None) -> str:
    if code is None:
        return "Unknown"
    return WMO_LABELS.get(code, "Variable conditions")


def _retail_signals(daily: list[dict], current_temp: float | None) -> list[dict]:
    signals: list[dict] = []
    rain_days = [d for d in daily if (d.get("precip_mm") or 0) >= 2 or d.get("weather_code") in RAIN_CODES]
    if rain_days:
        dates = ", ".join(d["date"] for d in rain_days[:3])
        signals.append(
            {
                "category": "Rain Gear",
                "impact": "high" if any(d.get("precip_mm", 0) >= 10 for d in rain_days) else "medium",
                "description": f"Rain expected ({dates}) — increase umbrella and rain gear stock",
            }
        )

    hot_days = [d for d in daily if (d.get("temp_max_c") or 0) >= HEAT_THRESHOLD_C]
    if hot_days or (current_temp and current_temp >= HEAT_THRESHOLD_C):
        max_t = max([d.get("temp_max_c", 0) for d in hot_days] + ([current_temp] if current_temp else [0]))
        signals.append(
            {
                "category": "Beverages",
                "impact": "high" if max_t >= 36 else "medium",
                "description": f"Heat up to {max_t:.0f}°C — cold drinks and ice cream demand likely up",
            }
        )

    weekend = [d for d in daily if datetime.fromisoformat(d["date"]).weekday() >= 5]
    if len(weekend) >= 1 and not signals:
        signals.append(
            {
                "category": "Snacks",
                "impact": "medium",
                "description": "Weekend footfall expected — keep snacks and beverages stocked",
            }
        )
    return signals


def _fetch_open_meteo(lat: float, lon: float, tz: str = "Asia/Kolkata") -> dict | None:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,weather_code,precipitation,relative_humidity_2m,wind_speed_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone": tz,
        "forecast_days": 5,
    }
    try:
        resp = httpx.get(url, params=params, timeout=12)
        resp.raise_for_status()
        data = resp.json()
        current = data.get("current", {})
        daily_raw = data.get("daily", {})
        dates = daily_raw.get("time", [])
        daily = []
        for i, dt in enumerate(dates):
            code = daily_raw.get("weather_code", [None] * len(dates))[i]
            daily.append(
                {
                    "date": dt,
                    "temp_max_c": daily_raw.get("temperature_2m_max", [None] * len(dates))[i],
                    "temp_min_c": daily_raw.get("temperature_2m_min", [None] * len(dates))[i],
                    "precip_mm": daily_raw.get("precipitation_sum", [0] * len(dates))[i],
                    "weather_code": code,
                    "condition": _wmo_label(code),
                }
            )
        cur_code = current.get("weather_code")
        cur_temp = current.get("temperature_2m")
        return {
            "current": {
                "temp_c": cur_temp,
                "condition": _wmo_label(cur_code),
                "weather_code": cur_code,
                "precipitation_mm": current.get("precipitation"),
                "humidity_pct": current.get("relative_humidity_2m"),
                "wind_kmh": current.get("wind_speed_10m"),
            },
            "daily": daily,
            "retail_signals": _retail_signals(daily, cur_temp),
            "source": "open-meteo",
        }
    except Exception:
        return None


def _fetch_openweather(lat: float, lon: float, api_key: str) -> dict | None:
    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {"lat": lat, "lon": lon, "appid": api_key, "units": "metric", "cnt": 40}
    try:
        resp = httpx.get(url, params=params, timeout=12)
        resp.raise_for_status()
        data = resp.json()
        city = data.get("city", {})
        list_items = data.get("list", [])
        if not list_items:
            return None

        first = list_items[0]
        current = {
            "temp_c": first["main"]["temp"],
            "condition": first["weather"][0]["description"].title() if first.get("weather") else "Unknown",
            "weather_code": None,
            "precipitation_mm": first.get("rain", {}).get("3h", 0),
            "humidity_pct": first["main"].get("humidity"),
            "wind_kmh": first.get("wind", {}).get("speed", 0) * 3.6,
        }

        by_day: dict[str, dict] = {}
        for item in list_items:
            day = item["dt_txt"][:10]
            if day not in by_day:
                by_day[day] = {"temps": [], "precip": 0.0, "conditions": []}
            by_day[day]["temps"].append(item["main"]["temp"])
            by_day[day]["precip"] += item.get("rain", {}).get("3h", 0)
            if item.get("weather"):
                by_day[day]["conditions"].append(item["weather"][0]["main"])

        daily = []
        for day in sorted(by_day.keys())[:5]:
            agg = by_day[day]
            cond = max(set(agg["conditions"]), key=agg["conditions"].count) if agg["conditions"] else "Clear"
            daily.append(
                {
                    "date": day,
                    "temp_max_c": max(agg["temps"]),
                    "temp_min_c": min(agg["temps"]),
                    "precip_mm": round(agg["precip"], 1),
                    "weather_code": None,
                    "condition": cond,
                }
            )

        return {
            "current": current,
            "daily": daily,
            "retail_signals": _retail_signals(daily, current["temp_c"]),
            "source": "openweather",
            "city_name": city.get("name"),
        }
    except Exception:
        return None


def _mock_forecast(location: str, lat: float, lon: float) -> dict:
    """Fallback when APIs unreachable — still location-tagged."""
    return {
        "current": {"temp_c": 30.0, "condition": "Partly cloudy", "weather_code": 2, "precipitation_mm": 0, "humidity_pct": 70, "wind_kmh": 12},
        "daily": [
            {"date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "temp_max_c": 32, "temp_min_c": 26, "precip_mm": 0, "condition": "Partly cloudy"},
        ],
        "retail_signals": [
            {"category": "Beverages", "impact": "medium", "description": f"Weekend warmth near {location.split(',')[0]} — keep cold drinks stocked"},
        ],
        "source": "demo",
    }


def fetch_store_weather(
    lat: float,
    lon: float,
    location: str = "",
    tz: str = "Asia/Kolkata",
    store_id: int | None = None,
    use_cache: bool = True,
) -> dict:
    settings = get_settings()
    cache_key = f"weather:store:{store_id}" if store_id else f"weather:{lat:.4f}:{lon:.4f}"

    if use_cache and store_id is not None:
        try:
            r = redis.from_url(settings.redis_url)
            cached = r.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    payload: dict | None = None
    if settings.openweather_api_key:
        payload = _fetch_openweather(lat, lon, settings.openweather_api_key)
    if not payload:
        payload = _fetch_open_meteo(lat, lon, tz)
    if not payload:
        payload = _mock_forecast(location or f"{lat},{lon}", lat, lon)

    payload["location"] = location
    payload["lat"] = lat
    payload["lon"] = lon
    payload["fetched_at"] = datetime.now(timezone.utc).isoformat()

    if use_cache and store_id is not None:
        try:
            r = redis.from_url(settings.redis_url)
            r.setex(cache_key, 1800, json.dumps(payload))  # 30 min cache
        except Exception:
            pass

    return payload
