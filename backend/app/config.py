from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    google_client_id: str
    google_client_secret: str
    database_url: str
    smallest_api_key: str
    secret_key: str
    
    # App settings
    app_name: str = "AI Scheduling Agent"
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]
    
    # OAuth
    google_redirect_uri: str = "http://localhost:8000/api/auth/callback"
    google_scopes: list[str] = [
        "openid",
        "email",
        "profile",
        "https://www.googleapis.com/auth/calendar",
    ]
    
    # Token settings
    access_token_expire_minutes: int = 60
    
    # Cookie security (set True when deployed over HTTPS)
    cookie_secure: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    return Settings()
