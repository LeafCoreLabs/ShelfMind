from app.config import get_settings
from app.services.signals.base import BaseSignalProvider
from app.services.signals.events import MetaGraphProvider, MockEventsProvider
from app.services.signals.trends import GoogleTrendsProvider, MockTrendsProvider
from app.services.signals.weather import MockWeatherProvider, OpenWeatherProvider


def get_signal_providers() -> list[BaseSignalProvider]:
    settings = get_settings()
    providers: list[BaseSignalProvider] = []

    if settings.openweather_api_key:
        providers.append(
            OpenWeatherProvider(settings.openweather_api_key, settings.store_lat, settings.store_lon)
        )
    else:
        providers.append(MockWeatherProvider())

    if settings.google_trends_enabled:
        providers.append(GoogleTrendsProvider())
    else:
        providers.append(MockTrendsProvider())

    if settings.meta_graph_token:
        providers.append(MetaGraphProvider(settings.meta_graph_token, settings.store_lat, settings.store_lon))
    else:
        providers.append(MockEventsProvider())

    return providers
