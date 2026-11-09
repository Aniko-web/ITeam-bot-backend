import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "MLBB Esports TMA & Bot Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "9064445555:AAF4Nm0YzZK6ykRPJbLv_MuFOkPtTNwsxQ8")
    TELEGRAM_BOT_USERNAME: str = os.getenv("TELEGRAM_BOT_USERNAME", "YourMlbbBot")
    TMA_WEBAPP_URL: str = os.getenv("TMA_WEBAPP_URL", "https://mlbb-esports.telegram.app")
    
    # Database (Default async SQLite for immediate zero-config local runs, asyncpg for PostgreSQL)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./mlbb_platform.db")
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://web.telegram.org",
        "https://t.me"
    ]
    
    # Ready Check Parameters
    READY_CHECK_WINDOW_SECONDS: int = 300  # 5 minutes confirmation window
    PENALTY_KARMA_UNREADY: int = 5
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

