import hmac
import hashlib
import json
import urllib.parse
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import HTTPException, Security, status, Header, Depends
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

init_data_header = APIKeyHeader(name="X-Telegram-Init-Data", auto_error=False)
dev_user_header = APIKeyHeader(name="X-Dev-Telegram-Id", auto_error=False)

def verify_telegram_init_data(init_data: str, bot_token: str) -> Optional[Dict[str, Any]]:
    """
    Validates Telegram WebApp initData using HMAC-SHA256.
    Follows official Telegram specification:
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    try:
        parsed_data = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        if "hash" not in parsed_data:
            return None

        received_hash = parsed_data.pop("hash")

        # Key-value pairs sorted in alphabetical order, joined by newline
        sorted_pairs = sorted([f"{k}={v}" for k, v in parsed_data.items()])
        data_check_string = "\n".join(sorted_pairs)

        # secret_key = HMAC_SHA256("WebAppData", bot_token)
        secret_key = hmac.new(
            key=b"WebAppData",
            msg=bot_token.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()

        # calculated_hash = HMAC_SHA256(secret_key, data_check_string)
        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode("utf-8"),
            digestmod=hashlib.sha256
        ).hexdigest()

        if calculated_hash.lower() != received_hash.lower():
            return None

        # Verify freshness (within 48 hours)
        auth_date = int(parsed_data.get("auth_date", 0))
        current_timestamp = int(datetime.now(timezone.utc).timestamp())
        if current_timestamp - auth_date > 86400 * 2:
            return None

        # Parse user payload
        if "user" in parsed_data:
            parsed_data["user"] = json.loads(parsed_data["user"])

        return parsed_data
    except Exception:
        return None

async def get_current_user(
    init_data_raw: Optional[str] = Security(init_data_header),
    dev_user_id: Optional[str] = Security(dev_user_header),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency that authenticates the Telegram user via native initData HMAC,
    with developer mock fallback for local testing.
    Automatically provisions new User record if not yet registered.
    """
    telegram_id: Optional[int] = None
    user_payload: Dict[str, Any] = {}

    if init_data_raw:
        verified = verify_telegram_init_data(init_data_raw, settings.TELEGRAM_BOT_TOKEN)
        if verified and "user" in verified:
            user_payload = verified["user"]
            telegram_id = int(user_payload.get("id"))
        else:
            # If verification fails in production, reject
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Telegram initData signature."
            )
    elif dev_user_id:
        # Developer testing mode
        try:
            telegram_id = int(dev_user_id)
            user_payload = {
                "id": telegram_id,
                "first_name": "ProPlayer",
                "username": f"player_{telegram_id}"
            }
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid X-Dev-Telegram-Id header")
    else:
        # Default mock user for testing if no headers provided
        telegram_id = 999888777
        user_payload = {
            "id": telegram_id,
            "first_name": "DemoCaptain",
            "username": "democaptain"
        }

    # Fetch from database
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalars().first()

    if not user:
        # Auto-provision user record
        user = User(
            telegram_id=telegram_id,
            username=user_payload.get("username"),
            first_name=user_payload.get("first_name", "MLBB Player"),
            last_name=user_payload.get("last_name"),
            avatar_url=user_payload.get("photo_url"),
            mlbb_id="58923411",
            server_id="2048",
            in_game_nickname=user_payload.get("username", "MLBB_Hero"),
            main_roles=["Jungler", "Mid Laner"],
            top_heroes=["Ling", "Fanny", "Gusion"],
            current_rank="Mythic",
            highest_rank="Mythic Glory",
            current_stars=28,
            karma_score=100,
            is_lfg_active=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been suspended due to low community karma or policy violations."
        )

    return user

