from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional
import json

from app.config import get_settings
from app.models.user import User
from app.models.oauth_token import OAuthToken
from app.services.encryption import encrypt_token, decrypt_token

settings = get_settings()

def create_oauth_flow() -> Flow:
    """Create Google OAuth flow."""
    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri],
        }
    }
    flow = Flow.from_client_config(
        client_config,
        scopes=settings.google_scopes,
        redirect_uri=settings.google_redirect_uri,
    )
    return flow

def get_authorization_url() -> tuple[str, str]:
    """Get authorization URL and state."""
    flow = create_oauth_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url, state

def exchange_code_for_tokens(code: str, state: str) -> dict:
    """Exchange authorization code for tokens."""
    flow = create_oauth_flow()
    flow.fetch_token(code=code)
    creds = flow.credentials
    return {
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "expiry": creds.expiry,
        "token_type": creds.token_type or "Bearer",
    }

def get_user_info(access_token: str) -> dict:
    """Get user info from Google."""
    creds = Credentials(token=access_token)
    service = build("oauth2", "v2", credentials=creds)
    user_info = service.userinfo().get().execute()
    return user_info

def upsert_user_and_token(db: Session, user_info: dict, token_data: dict) -> User:
    """Create or update user and their OAuth tokens."""
    user = db.query(User).filter(User.email == user_info["email"]).first()
    if not user:
        user = User(
            email=user_info["email"],
            name=user_info.get("name", user_info["email"]),
        )
        db.add(user)
        db.flush()
    
    token = db.query(OAuthToken).filter(OAuthToken.user_id == user.id).first()
    encrypted_access = encrypt_token(token_data["access_token"])
    encrypted_refresh = encrypt_token(token_data["refresh_token"]) if token_data.get("refresh_token") else None
    
    if not token:
        token = OAuthToken(
            user_id=user.id,
            access_token=encrypted_access,
            refresh_token=encrypted_refresh,
            expiry=token_data.get("expiry"),
            token_type=token_data.get("token_type", "Bearer"),
        )
        db.add(token)
    else:
        token.access_token = encrypted_access
        if encrypted_refresh:
            token.refresh_token = encrypted_refresh
        token.expiry = token_data.get("expiry")
    
    db.commit()
    db.refresh(user)
    return user

def get_credentials_for_user(db: Session, user_id: int) -> Optional[Credentials]:
    """Get valid Google credentials for a user, refreshing if needed."""
    token = db.query(OAuthToken).filter(OAuthToken.user_id == user_id).first()
    if not token:
        return None
    
    access_token = decrypt_token(token.access_token)
    refresh_token = decrypt_token(token.refresh_token) if token.refresh_token else None
    
    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
    )
    
    if token.expiry:
        creds.expiry = token.expiry
    
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token.access_token = encrypt_token(creds.token)
        token.expiry = creds.expiry
        db.commit()
    
    return creds
