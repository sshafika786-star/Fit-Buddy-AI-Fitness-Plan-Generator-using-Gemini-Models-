from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FitBuddy – AI Fitness Plan Generator"
    database_url: str = "sqlite:///./data/fitbuddy.db"
    gemini_api_key: str = ""
    workout_model: str = "gemini-3.8-flash"
    nutrition_model: str = "gemini-3.8-flash"
    admin_token: str = "change-me"
    demo_mode: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
