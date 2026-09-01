"""
Application Configuration Settings for CAGED Backend.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings loaded from environment variables or defaults."""

    PROJECT_NAME: str = "CAGED"
    SERVICE_NAME: str = "caged"
    VERSION: str = "0.1.0"
    API_PREFIX: str = ""
    ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Database & Storage Configuration
    DATABASE_URL: str = "sqlite:///./caged.db"

    # Streaming Configuration
    WINDOW_SIZE_SECONDS: int = 300
    BUFFER_CAPACITY: int = 10000

    # False Alarm & Statistical Detection Configuration
    TARGET_FALSE_ALARM_RATE: float = 0.05
    HASH_SALT: str = "caged_default_secret_salt_2026"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
