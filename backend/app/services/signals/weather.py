from app.services.signals.base import BaseSignalProvider, SignalResult


class MockWeatherProvider(BaseSignalProvider):
    def fetch(self) -> list[SignalResult]:
        return [
            SignalResult(
                signal_type="weather",
                category="Rain Gear",
                value=3.4,
                description="Monsoon onset forecast — heavy rainfall expected this week",
            ),
            SignalResult(
                signal_type="weather",
                category="Beverages",
                value=2.0,
                description="Weekend heatwave — 38°C forecast Saturday–Sunday",
            ),
        ]


class OpenWeatherProvider(BaseSignalProvider):
    def __init__(self, api_key: str, lat: float, lon: float):
        self.api_key = api_key
        self.lat = lat
        self.lon = lon

    def fetch(self) -> list[SignalResult]:
        import httpx

        url = "https://api.openweathermap.org/data/2.5/forecast"
        params = {"lat": self.lat, "lon": self.lon, "appid": self.api_key, "units": "metric"}
        try:
            resp = httpx.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            temps = [item["main"]["temp"] for item in data.get("list", [])[:8]]
            rain = any("rain" in item for item in data.get("list", [])[:8])
            avg_temp = sum(temps) / len(temps) if temps else 30
            results = []
            if rain:
                results.append(
                    SignalResult("weather", "Rain Gear", 3.4, "Rain forecast detected — umbrella demand likely up")
                )
            if avg_temp >= 35:
                results.append(
                    SignalResult("weather", "Beverages", 2.0, f"High temps ({avg_temp:.0f}°C) — cold beverage demand up")
                )
            return results or MockWeatherProvider().fetch()
        except Exception:
            return MockWeatherProvider().fetch()
