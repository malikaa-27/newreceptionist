from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.database import engine, Base
from app.models import User, OAuthToken, Meeting
from app.api import auth, calendar, agent
from app.middleware.token_refresh import TokenRefreshMiddleware

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    description="AI-powered meeting scheduling agent with Google Calendar integration",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
)

# Token refresh middleware
app.add_middleware(TokenRefreshMiddleware)

# Routers
app.include_router(auth.router)
app.include_router(calendar.router)
app.include_router(agent.router)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.app_name}
