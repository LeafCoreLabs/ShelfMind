from app.services.signals.base import BaseSignalProvider, SignalResult


class MockTrendsProvider(BaseSignalProvider):
    def fetch(self) -> list[SignalResult]:
        return [
            SignalResult(
                signal_type="trends",
                category="Rain Gear",
                value=2.8,
                description="Google Trends: 'umbrella' searches up 180% in Mumbai metro",
            ),
            SignalResult(
                signal_type="trends",
                category="Snacks",
                value=0.6,
                description="Instant noodle search interest down — holiday season dip",
            ),
        ]


class GoogleTrendsProvider(BaseSignalProvider):
    def fetch(self) -> list[SignalResult]:
        return MockTrendsProvider().fetch()
