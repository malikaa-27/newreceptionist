from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    google_client_id: str = ""
    google_client_secret: str = ""
    database_url: str = "postgresql://user:password@localhost:5432/scheduler"
    smallest_api_key: str = ""
    secret_key: str = "change-me-in-production"
    encryption_key: str = ""  # Fernet key for token encryption
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"
    environment: str = "development"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
