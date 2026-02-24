from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from ..models import User, OAuthToken
from ..services.encryption import encrypt_token, decrypt_token
from ..config import get_settings

settings = get_settings()

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/calendar",
]


def get_or_create_user(db: Session, email: str, name: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, name=name)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def upsert_oauth_token(
    db: Session,
    user: User,
    access_token: str,
    refresh_token: Optional[str],
    expiry: Optional[datetime],
    token_type: str = "Bearer",
) -> OAuthToken:
    token_row = db.query(OAuthToken).filter(OAuthToken.user_id == user.id).first()
    if token_row:
        token_row.access_token = encrypt_token(access_token)
        if refresh_token:
            token_row.refresh_token = encrypt_token(refresh_token)
        token_row.expiry = expiry
        token_row.token_type = token_type
    else:
        token_row = OAuthToken(
            user_id=user.id,
            access_token=encrypt_token(access_token),
            refresh_token=encrypt_token(refresh_token) if refresh_token else None,
            expiry=expiry,
            token_type=token_type,
        )
        db.add(token_row)
    db.commit()
    db.refresh(token_row)
    return token_row


def get_credentials(db: Session, user_id) -> Optional[Credentials]:
    """Load and auto-refresh credentials from the database."""
    token_row = db.query(OAuthToken).filter(OAuthToken.user_id == user_id).first()
    if not token_row:
        return None

    access_token = decrypt_token(token_row.access_token)
    refresh_token = decrypt_token(token_row.refresh_token) if token_row.refresh_token else None

    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=SCOPES,
        expiry=token_row.expiry,
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        upsert_oauth_token(
            db,
            db.query(User).filter(User.id == user_id).first(),
            creds.token,
            creds.refresh_token,
            creds.expiry,
        )

    return creds
