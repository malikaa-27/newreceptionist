from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from datetime import datetime, timezone

from app.database import SessionLocal
from app.config import get_settings

settings = get_settings()

class TokenRefreshMiddleware(BaseHTTPMiddleware):
    """Middleware to auto-refresh Google OAuth tokens before API calls."""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        session_token = request.cookies.get("session_token")
        
        if session_token and request.url.path.startswith("/api/"):
            try:
                payload = jwt.decode(session_token, settings.secret_key, algorithms=["HS256"])
                user_id = int(payload["sub"])
                
                # Check and refresh Google token if needed
                db = SessionLocal()
                try:
                    from app.services.oauth import get_credentials_for_user
                    get_credentials_for_user(db, user_id)
                finally:
                    db.close()
            except (JWTError, Exception):
                pass  # Continue even if refresh fails
        
        return await call_next(request)
