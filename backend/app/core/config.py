from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "NaijaWatch Intelligence System"
    APP_NAME: str = "NaijaWatch"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = "development"  # development | production

    APP_BASE_URL: str = "http://localhost:5173" # Override in .env

    # API Keys
    GROQ_API_KEY: Optional[str] = None
    ORS_API_KEY: Optional[str] = None

    # SMTP Settings
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None

    # Database (default is local SQLite for dev)
    DATABASE_URL: str = "sqlite:///./naijawatch.db"

    # Digest / Email Settings
    FROM_EMAIL: str = "updates@naijawatch.local"  # Override in .env

    @property
    def DB_URL(self) -> str:
        """Return the effective database URL.

        This prefers an explicit DATABASE_URL environment variable (useful for CI/production)
        while falling back to the configured value (e.g. from .env) for local development.
        """
        import os

        return os.environ.get("DATABASE_URL", self.DATABASE_URL)

    @property
    def is_sqlite(self) -> bool:
        return self.DB_URL.startswith("sqlite")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Instantiate as a singleton
settings = Settings()
config = settings
