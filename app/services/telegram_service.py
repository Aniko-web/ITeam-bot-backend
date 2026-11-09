import logging
import httpx
from typing import Optional, List
from app.core.config import settings

logger = logging.getLogger(__name__)

class TelegramNotificationService:
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = "HTML",
        reply_markup: Optional[dict] = None
    ) -> bool:
        if not self.bot_token:
            logger.warning("No Telegram Bot token configured; skipping notification.")
            return False

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(url, json=payload)
                return res.status_code == 200
        except Exception as e:
            logger.error(f"Error sending Telegram notification to {chat_id}: {e}")
            return False

    async def broadcast_scrim_ready_check(
        self,
        user_ids: List[int],
        scrim_id: str,
        match_time_str: str,
        format_str: str,
        host_tag: str,
        challenger_tag: str
    ):
        """
        Multilingual Scrim Ready Check alert sent exactly 10 minutes prior to scheduled scrim.
        """
        text = (
            f"⚔️ <b>MLBB SCRIM READY CHECK: {host_tag} vs {challenger_tag}</b>\n\n"
            f"⏱ <b>Match Time / Vaqt / Время:</b> {match_time_str}\n"
            f"🏆 <b>Format:</b> {format_str}\n\n"
            f"🇺🇿 <i>Iltimos, 5 daqiqa ichida tayyor ekanligingizni tasdiqlang. "
            f"Tasdiqlanmasa scrim bekor qilinadi va -5 Karma jarima beriladi.</i>\n\n"
            f"🇷🇺 <i>Подтвердите готовность в течение 5 минут во избежание отмены и штрафа -5 Кармы.</i>\n\n"
            f"🇬🇧 <i>Confirm readiness within 5 minutes. Unready players receive -5 Karma penalty.</i>"
        )
        markup = {
            "inline_keyboard": [
                [
                    {
                        "text": "✅ TASDIQLASH / ГОТОВ / READY",
                        "callback_data": f"ready_scrim:{scrim_id}"
                    }
                ],
                [
                    {
                        "text": "📱 Open Match Hub",
                        "web_app": {"url": f"{settings.TMA_WEBAPP_URL}/scrims/{scrim_id}"}
                    }
                ]
            ]
        }

        for uid in user_ids:
            await self.send_message(chat_id=uid, text=text, reply_markup=markup)

    async def broadcast_room_credentials(
        self,
        user_ids: List[int],
        room_id: str,
        password: str,
        match_title: str
    ):
        """
        Delivers custom MLBB room ID and password to all confirmed players.
        """
        text = (
            f"🚀 <b>MLBB CUSTOM ROOM CREDENTIALS / XONA MA'LUMOTLARI!</b>\n\n"
            f"🏆 <b>Match / O'yin:</b> {match_title}\n\n"
            f"🔑 <b>Room ID:</b> <code>{room_id}</code>\n"
            f"🔒 <b>Password / Parol:</b> <code>{password}</code>\n\n"
            f"🇺🇿 <i>MLBB > Custom > Join Private Room orqali kiring. Omad!</i>\n"
            f"🇷🇺 <i>Зайдите в MLBB > Свой бой > Войти по ID. Удачи!</i>\n"
            f"🇬🇧 <i>Open MLBB > Custom Room > Join Private Room. Good luck!</i>"
        )
        for uid in user_ids:
            await self.send_message(chat_id=uid, text=text)

telegram_service = TelegramNotificationService()
