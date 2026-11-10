import os
from typing import List, Union, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False
    )

    PROJECT_NAME: str = "MLBB Esports TMA & Bot Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Server Port / Host (Alwaysdata or VPS)
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = "9064445555:AAF4Nm0YzZK6ykRPJbLv_MuFOkPtTNwsxQ8"
    TELEGRAM_BOT_USERNAME: str = "YourMlbbBot"
    TMA_WEBAPP_URL: str = "https://mlbb-esports.telegram.app"
    BACKEND_API_URL: str = "http://localhost:8000/api/v1"
    
    # Database (Default async SQLite for immediate zero-config runs, asyncpg for PostgreSQL)
    DATABASE_URL: str = "sqlite+aiosqlite:///./mlbb_platform.db"
    POSTGRES_USER: Optional[str] = "mlbb_user"
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: Optional[str] = "mlbb_esports"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # CORS (Supports comma-separated URLs or JSON lists)
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://web.telegram.org",
        "https://t.me",
        "*"
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if not v or not v.strip():
                return ["*"]
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]
    
    # Ready Check Parameters
    READY_CHECK_WINDOW_SECONDS: int = 300  # 5 minutes confirmation window
    PENALTY_KARMA_UNREADY: int = 5

settings = Settings()
