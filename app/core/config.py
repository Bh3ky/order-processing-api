from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central application configuration.
    """

    # Application metadata
    app_name: str = "Order Processing API"
    app_version: str = "1.0.0"
    debug: bool = False

    # PostgreSQL connection URL used by SQLAlchemy
    database_url: str

    # Tell Pydantic where to load environment variables from
    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore unknown environment variables
    )

@lru_cache
def get_settings() -> Settings:
    """
    Return a cached instance of the Settings.
    """
    return Settings()


# Shared settings instance for the application
settings = get_settings()