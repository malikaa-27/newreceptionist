from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
import secrets

from app.database import get_db
from app.services.oauth import (
    get_authorization_url,
    exchange_code_for_tokens,
    get_user_info,
    upsert_user_and_token,
)
from app.config import get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()

def create_session_token(user_id: int, email: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")

def get_current_user(request: Request) -> dict:
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return {"user_id": int(payload["sub"]), "email": payload["email"]}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid session")

@router.get("/login")
async def login():
    """Initiate Google OAuth flow."""
    auth_url, state = get_authorization_url()
    response = RedirectResponse(url=auth_url)
    response.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=600,
    )
    return response

@router.get("/callback")
async def oauth_callback(
    code: str,
    state: str,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Handle Google OAuth callback."""
    stored_state = request.cookies.get("oauth_state")
    if not stored_state or stored_state != state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    
    try:
        token_data = exchange_code_for_tokens(code, state)
        user_info = get_user_info(token_data["access_token"])
        user = upsert_user_and_token(db, user_info, token_data)
        
        session_token = create_session_token(user.id, user.email)
        
        redirect_response = RedirectResponse(url=f"{settings.frontend_url}/chat")
        redirect_response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=settings.cookie_secure,
            samesite="lax",
            max_age=settings.access_token_expire_minutes * 60,
        )
        redirect_response.delete_cookie("oauth_state")
        return redirect_response
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth error: {str(e)}")

@router.post("/logout")
async def logout(response: Response):
    """Clear session cookie."""
    response.delete_cookie("session_token")
    return {"message": "Logged out successfully"}

@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current user info."""
    from app.models.user import User
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user.id, "email": user.email, "name": user.name, "timezone": user.timezone}
