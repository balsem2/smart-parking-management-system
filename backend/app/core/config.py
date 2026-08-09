import json
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SmartPark AI API"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./smartpark.db"
    cors_origins_raw: str = "http://localhost:5173,http://localhost:3000"
    seed_demo_data: bool = True
    visitor_max_hours: int = 6
    almost_full_threshold: float = 0.9
    first_hour_rate: float = 2.0
    additional_hour_rate: float = 1.0
    daily_max_rate: float = 15.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        value = self.cors_origins_raw.strip()
        if value.startswith("["):
            return list(json.loads(value))
        return [origin.strip() for origin in value.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
