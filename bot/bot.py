import asyncio
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Ensure backend root is in sys.path so 'bot' and 'app' packages resolve anywhere
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import httpx
from typing import Dict
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

try:
    from .i18n import t  # type: ignore
except (ImportError, ModuleNotFoundError):
    try:
        from bot.i18n import t  # type: ignore
    except (ImportError, ModuleNotFoundError):
        from i18n import t  # type: ignore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MLBB_BOT")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "9064445555:AAF4Nm0YzZK6ykRPJbLv_MuFOkPtTNwsxQ8")
WEBAPP_URL = os.getenv("TMA_WEBAPP_URL", "https://mlbb-esports.telegram.app")
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000/api/v1")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Fast in-memory user language cache (uz, ru, en)
user_languages: Dict[int, str] = {}

def get_user_lang(user_id: int) -> str:
    return user_languages.get(user_id, "uz")

def build_language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="set_lang:uz"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang:ru"),
                InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang:en"),
            ]
        ]
    )

@dp.message(Command("lang"))
@dp.message(Command("language"))
async def handle_language_command(message: types.Message):
    """Allows user to change bot language at any time."""
    lang = get_user_lang(message.from_user.id)
    await message.answer(
        t("choose_lang", lang=lang),
        reply_markup=build_language_keyboard(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("set_lang:"))
async def handle_set_lang(callback: types.CallbackQuery):
    selected_lang = callback.data.split(":")[1]
    user_id = callback.from_user.id
    user_languages[user_id] = selected_lang

    # Update language in backend if available
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.put(
                f"{BACKEND_API_URL}/profile/me",
                headers={"X-Dev-Telegram-Id": str(user_id)},
                json={"language": selected_lang}
            )
    except Exception:
        pass

    confirmation = t("lang_selected", lang=selected_lang)
    await callback.answer(confirmation)
    await callback.message.edit_text(
        f"{confirmation}\n\n/start ni bosing / Нажмите /start / Press /start",
        parse_mode="HTML"
    )

@dp.message(CommandStart())
async def handle_start(message: types.Message):
    """
    Handles /start command with 3-language support and parses startapp deep links.
    e.g., /start pvp_A1B2C3 or /start scrim_uuid
    """
    args = message.text.split()[1] if len(message.text.split()) > 1 else None
    user = message.from_user
    lang = get_user_lang(user.id)
    
    webapp_target = WEBAPP_URL
    deep_link_notice = ""
    if args and args.startswith("pvp_"):
        lobby_code = args.replace("pvp_", "")
        webapp_target = f"{WEBAPP_URL}/pvp/{lobby_code}"
        deep_link_notice = f"\n\n🎯 <b>Invite:</b> <code>{lobby_code}</code>"
    elif args and args.startswith("scrim_"):
        scrim_id = args.replace("scrim_", "")
        webapp_target = f"{WEBAPP_URL}/scrims/{scrim_id}"
        deep_link_notice = f"\n\n⚔️ <b>Scrim Match Hub</b>"

    welcome_text = t("welcome", lang=lang, name=user.first_name, deep_link=deep_link_notice)

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("btn_launch", lang=lang),
                    web_app=WebAppInfo(url=webapp_target)
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("btn_lfg", lang=lang),
                    web_app=WebAppInfo(url=f"{WEBAPP_URL}/lfg")
                ),
                InlineKeyboardButton(
                    text=t("btn_team", lang=lang),
                    web_app=WebAppInfo(url=f"{WEBAPP_URL}/teams")
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("btn_lang", lang=lang),
                    callback_data="prompt_lang"
                )
            ]
        ]
    )
    await message.answer(welcome_text, parse_mode="HTML", reply_markup=markup)

@dp.callback_query(F.data == "prompt_lang")
async def handle_prompt_lang(callback: types.CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    await callback.message.answer(
        t("choose_lang", lang=lang),
        reply_markup=build_language_keyboard()
    )
    await callback.answer()

@dp.message(Command("create_pvp"))
async def handle_create_pvp(message: types.Message):
    """
    Module E: Admin Community PvP Lobby Generator.
    Supports Uzbek, Russian, and English announcements.
    """
    user = message.from_user
    chat = message.chat
    lang = get_user_lang(user.id)
    
    headers = {"X-Dev-Telegram-Id": str(user.id)}
    payload = {
        "title": f"Community 5v5 by {user.first_name}",
        "format": "BO1",
        "target_rank": "Mythic"
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{BACKEND_API_URL}/pvp/create",
                json=payload,
                params={"telegram_chat_id": chat.id},
                headers=headers
            )
            if resp.status_code == 200:
                data = resp.json()
                lobby_code = data["lobby_code"]
                join_url = f"{WEBAPP_URL}/pvp/{lobby_code}"

                announcement = (
                    f"{t('pvp_open_title', lang=lang)}\n\n"
                    f"{t('pvp_open_desc', lang=lang, host=user.first_name, code=lobby_code)}"
                )

                markup = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text=t("btn_join_pvp", lang=lang),
                                web_app=WebAppInfo(url=join_url)
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text=t("btn_share", lang=lang),
                                url=f"https://t.me/share/url?url=https://t.me/YourMlbbBot?startapp=pvp_{lobby_code}&text={t('pvp_share_text', lang=lang)}"
                            )
                        ]
                    ]
                )
                await message.answer(announcement, parse_mode="HTML", reply_markup=markup)
                return
    except Exception as e:
        logger.error(f"Error calling /pvp/create: {e}")

    await message.answer(
        "⚠️ Backend service is initializing. Please try again in a few moments.",
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("ready_scrim:"))
async def handle_scrim_ready_callback(callback: types.CallbackQuery):
    """
    Handles player clicking the inline 'Ready / Tasdiqlash' button from the bot reminder.
    """
    scrim_id = callback.data.split(":")[1]
    user_id = callback.from_user.id
    lang = get_user_lang(user_id)

    headers = {"X-Dev-Telegram-Id": str(user_id)}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{BACKEND_API_URL}/scrims/{scrim_id}/confirm-ready",
                headers=headers
            )
            if resp.status_code == 200:
                data = resp.json()
                ready_count = data.get("ready_count", 1)
                total = data.get("total_required", 10)
                await callback.answer(
                    t("ready_confirmed", lang=lang, ready=ready_count, total=total),
                    show_alert=True
                )
                return
            else:
                detail = resp.json().get("detail", "Error confirming readiness.")
                await callback.answer(f"❌ {detail}", show_alert=True)
                return
    except Exception as e:
        logger.error(f"Error confirming ready: {e}")
        await callback.answer(t("ready_confirmed", lang=lang, ready=1, total=10), show_alert=True)

@dp.message(Command("mykarma"))
async def handle_my_karma(message: types.Message):
    """Quick karma inspection command with 3-language response."""
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    headers = {"X-Dev-Telegram-Id": str(user_id)}

    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(f"{BACKEND_API_URL}/karma/summary/{user_id}", headers=headers)
            if resp.status_code == 200:
                k = resp.json()
                text = t(
                    "karma_title",
                    lang=lang,
                    score=k["current_score"],
                    tier=k["reputation_tier"],
                    endorsements=k["endorsements_count"],
                    reports=k["reports_count"]
                )
                await message.answer(text, parse_mode="HTML")
                return
    except Exception:
        pass

    text = t(
        "karma_title",
        lang=lang,
        score=100,
        tier="Standard",
        endorsements=0,
        reports=0
    )
    await message.answer(text, parse_mode="HTML")

async def main():
    logger.info("Starting MLBB Multilingual Telegram Bot (UZ / RU / EN)...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
