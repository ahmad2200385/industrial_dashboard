"""Application configuration management.

Handles all configuration from environment variables with proper
validation and defaults. Follows 12-factor app principles.
"""

import os
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


BASE_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BASE_DIR / ".env"

if load_dotenv:
    load_dotenv(dotenv_path=ENV_FILE, override=False)


class Settings:
    """Application settings loaded from environment variables.

    All configuration is externalized through environment variables
    for easy deployment across different environments.
    """

    # Application metadata
    APP_NAME: str = os.getenv("APP_NAME", "Smart Factory API")
    APP_VERSION: str = os.getenv("APP_VERSION", "3.0.0")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    DEBUG: bool = APP_ENV.lower() in {"dev", "development"}

    # Logging configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", str(BASE_DIR / "logs" / "app.log"))
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Database configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/smart_factory",
    )
    DATABASE_POOL_SIZE: int = int(os.getenv("DATABASE_POOL_SIZE", "20"))
    DATABASE_MAX_OVERFLOW: int = int(os.getenv("DATABASE_MAX_OVERFLOW", "40"))
    DATABASE_POOL_TIMEOUT: int = int(os.getenv("DATABASE_POOL_TIMEOUT", "30"))

    # Redis configuration
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD", None)
    REDIS_SSL: bool = os.getenv("REDIS_SSL", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    REDIS_CACHE_TTL: int = int(os.getenv("REDIS_CACHE_TTL", "3600"))

    # Alert configuration
    ALERT_TEMPERATURE_THRESHOLD: float = float(
        os.getenv("ALERT_TEMPERATURE_THRESHOLD", "80")
    )
    ALERT_INFO_TTL_SECONDS: int = int(
        os.getenv("ALERT_INFO_TTL_SECONDS", "900")
    )
    ALERT_WARNING_TTL_SECONDS: int = int(
        os.getenv("ALERT_WARNING_TTL_SECONDS", "1800")
    )
    ALERT_CRITICAL_TTL_SECONDS: int = int(
        os.getenv("ALERT_CRITICAL_TTL_SECONDS", "3600")
    )
    ALERT_EXPIRY_SWEEP_SECONDS: int = int(
        os.getenv("ALERT_EXPIRY_SWEEP_SECONDS", "15")
    )

    # Database initialization
    AUTO_CREATE_SCHEMA: bool = os.getenv("AUTO_CREATE_SCHEMA", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    # CORS configuration
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
    ]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    @classmethod
    def validate(cls) -> None:
        """Validate critical configuration settings."""
        if not cls.DATABASE_URL:
            raise ValueError("DATABASE_URL must be configured")

        if cls.ALERT_TEMPERATURE_THRESHOLD < -50 or cls.ALERT_TEMPERATURE_THRESHOLD > 150:
            raise ValueError("ALERT_TEMPERATURE_THRESHOLD must be between -50 and 150")

        if cls.REDIS_PORT < 1 or cls.REDIS_PORT > 65535:
            raise ValueError("REDIS_PORT must be valid port number")

    @classmethod
    def to_dict(cls) -> dict:
        """Export settings as dictionary."""
        return {
            "APP_NAME": cls.APP_NAME,
            "APP_VERSION": cls.APP_VERSION,
            "APP_ENV": cls.APP_ENV,
            "DEBUG": cls.DEBUG,
            "LOG_LEVEL": cls.LOG_LEVEL,
            "DATABASE_URL": cls.DATABASE_URL,
            "REDIS_HOST": cls.REDIS_HOST,
            "REDIS_PORT": cls.REDIS_PORT,
            "ALERT_TEMPERATURE_THRESHOLD": cls.ALERT_TEMPERATURE_THRESHOLD,
        }


# Validate configuration on import
try:
    settings = Settings()
    settings.validate()
except ValueError as e:
    raise RuntimeError(f"Configuration error: {str(e)}") from e
