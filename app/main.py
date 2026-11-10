import os
import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import engine, Base
from app.core.redis import redis_manager
from app.api.profiles import router as profiles_router
from app.api.teams import router as teams_router
from app.api.scrims import router as scrims_router
from app.api.karma import router as karma_router
from app.api.pvp import router as pvp_router
from app.api.economy import router as economy_router
from app.services.ready_check_scheduler import start_ready_check_scheduler

logger = logging.getLogger("MAIN")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Initialize Redis connection (falls back to in-memory cache if offline)
    await redis_manager.init()
    # Launch background ready check monitor task
    scheduler_task = asyncio.create_task(start_ready_check_scheduler())
    yield
    # Shutdown
    scheduler_task.cancel()
    await redis_manager.close()
    await engine.dispose()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware (Multi-Server & Telegram Webview support)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"],
    allow_origin_regex=r"^https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
api_v1 = FastAPI()
app.include_router(profiles_router, prefix=settings.API_V1_STR)
app.include_router(teams_router, prefix=settings.API_V1_STR)
app.include_router(scrims_router, prefix=settings.API_V1_STR)
app.include_router(karma_router, prefix=settings.API_V1_STR)
app.include_router(pvp_router, prefix=settings.API_V1_STR)
app.include_router(economy_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {
        "status": "online",
        "platform": "MLBB Esports Telegram Mini App API",
        "version": settings.VERSION,
        "docs": "/docs"
    }

@app.get("/health")
async def health():
    return {
        "database": "connected",
        "redis": "connected" if redis_manager.is_connected else "in_memory_fallback"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

