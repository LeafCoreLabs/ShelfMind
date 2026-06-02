from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://shelfmind:shelfmind@pgbouncer:5432/shelfmind"
    database_url_sync: str = "postgresql://shelfmind:shelfmind@pgbouncer:5432/shelfmind"
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"

    s3_endpoint: str = "http://minio:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "shelfmind-reports"

    openai_api_key: str = ""
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    openweather_api_key: str = ""
    google_trends_enabled: bool = False
    meta_graph_token: str = ""

    store_lat: float = 19.0760
    store_lon: float = 72.8777
    secret_key: str = "change-me"
    jwt_secret: str = ""
    access_token_expire_minutes: int = 480
    algorithm: str = "HS256"

    @property
    def effective_jwt_secret(self) -> str:
        return self.jwt_secret or self.secret_key

    @property
    def llm_api_key(self) -> str:
        return self.groq_api_key or self.openai_api_key

    @property
    def llm_model(self) -> str:
        if self.groq_api_key:
            return self.groq_model
        if self.openai_api_key:
            return "gpt-4o-mini"
        return ""

    @property
    def llm_base_url(self) -> str | None:
        if self.groq_api_key:
            return self.groq_base_url
        return None

    @property
    def llm_provider(self) -> str:
        if self.groq_api_key:
            return "groq"
        if self.openai_api_key:
            return "openai"
        return "demo"


@lru_cache
def get_settings() -> Settings:
    return Settings()
