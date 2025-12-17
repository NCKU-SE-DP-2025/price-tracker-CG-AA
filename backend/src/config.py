from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    The application will fail to start if required variables are missing.
    """

    JWT_SECRET_KEY: str
    OPENAI_API_KEY: str
    JWT_ALGORITHM: str = "HS256"

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


def get_settings() -> Settings:
    """
    Get application settings.
    Raises ValidationError if required environment variables are missing.
    """
    return Settings()


# Singleton instance - will raise error at import time if env vars are missing
settings = Settings()
