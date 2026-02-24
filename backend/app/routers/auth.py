"""
Google OAuth 2.0 authentication endpoints.
"""
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.google_auth import get_or_create_user, upsert_oauth_token, SCOPES, get_credentials
from ..schemas.schemas import UserOut
from ..config import get_settings

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["auth"])

_SESSION_KEY = "user_id"


def _build_flow(state: Optional[str] = None) -> Flow:
    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [f"{settings.backend_url}/auth/callback"],
        }
    }
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        state=state,
    )
    flow.redirect_uri = f"{settings.backend_url}/auth/callback"
    return flow


@router.get("/login")
async def login(request: Request):
    """Redirect user to Google OAuth consent screen."""
    flow = _build_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    request.session["oauth_state"] = state
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def callback(request: Request, db: Session = Depends(get_db)):
    """Handle OAuth callback, store tokens, set session cookie."""
    state = request.session.get("oauth_state")
    flow = _build_flow(state=state)
    flow.fetch_token(
        authorization_response=str(request.url),
        state=state,
    )
    creds = flow.credentials

    # Fetch user profile
    userinfo_service = build("oauth2", "v2", credentials=creds)
    user_info = userinfo_service.userinfo().get().execute()

    email = user_info["email"]
    name = user_info.get("name", email)

    user = get_or_create_user(db, email=email, name=name)

    expiry: Optional[datetime] = None
    if creds.expiry:
        expiry = creds.expiry.replace(tzinfo=timezone.utc) if creds.expiry.tzinfo is None else creds.expiry

    upsert_oauth_token(
        db,
        user=user,
        access_token=creds.token,
        refresh_token=creds.refresh_token,
        expiry=expiry,
        token_type="Bearer",
    )

    request.session[_SESSION_KEY] = str(user.id)
    return RedirectResponse(url=f"{settings.frontend_url}/chat")


@router.get("/me", response_model=UserOut)
async def me(request: Request, db: Session = Depends(get_db)):
    """Return the authenticated user's profile."""
    user_id = request.session.get(_SESSION_KEY)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    from ..models import User
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/logout")
async def logout(request: Request, response: Response):
    """Clear the session."""
    request.session.clear()
    return {"message": "Logged out"}
