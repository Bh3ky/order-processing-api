from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central application configuration.

    Values are loaded from environment variables or a env file.
    Pydantic automatically validates and converts them to the
    appropriate Python types.
    """

    # Application metadata
    app_name: str = "Order Processing API"
    app_version: str = "1.0.0"

    # Development settings
    debug: bool = False

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

    Configuration should only be loaded once during the
    application's lifetime.
    """
    return Settings()


# Shared settings instance for the application
settings = get_settings()