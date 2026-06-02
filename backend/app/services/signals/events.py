from app.services.signals.base import BaseSignalProvider, SignalResult


class MockEventsProvider(BaseSignalProvider):
    def fetch(self) -> list[SignalResult]:
        return [
            SignalResult(
                signal_type="events",
                category="Snacks",
                value=0.4,
                description="Local college hostel closed for holidays — instant noodle demand down",
            ),
            SignalResult(
                signal_type="events",
                category="Beverages",
                value=1.5,
                description="Weekend street food festival nearby — foot traffic boost expected",
            ),
        ]


class MetaGraphProvider(BaseSignalProvider):
    def __init__(self, token: str, lat: float, lon: float):
        self.token = token
        self.lat = lat
        self.lon = lon

    def fetch(self) -> list[SignalResult]:
        return MockEventsProvider().fetch()
