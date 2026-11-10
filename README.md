# ITeam — Mobile Legends Esports Platform (Backend & Bot Engine)

Yuqori yuklamalarga mo‘ljallangan **ITeam** MLBB platformasining FastAPI REST API, aiogram 3.x Telegram Bot demoni, PostgreSQL va Redis kesh tizimi.

---

## 🚀 Texnologiyalar Steki
* **Til & Freymvork:** Python 3.11, FastAPI, Pydantic v2
* **Telegram Bot:** aiogram 3.x (Async polling & webhooks)
* **Ma'lumotlar bazasi:** PostgreSQL 15 (SQLAlchemy 2.0 + asyncpg)
* **Kesh & Xabarlar navbati:** Redis 7 (Aiocache, Scrim Ready Check 30s timers)
* **Konteynerizatsiya:** Docker & Docker Compose

---

## ⚙️ Tezkor O‘rnatish (Docker orqali)

### 1. Repository'ni klon qiling:
```bash
git clone https://github.com/Aniko-web/ITeam-bot-backend.git backend
cd backend
```

### 2. Muhit sozlamalarini kiriting (.env):
```bash
cp .env.example .env
nano .env
```
Kerakli parametrlarni to‘ldiring:
```ini
TELEGRAM_BOT_TOKEN=9064445555:AAF4Nm0YzZK6ykRPJbLv_MuFOkPtTNwsxQ8
TMA_WEBAPP_URL=https://iteam.domain.com
CORS_ORIGINS=https://iteam.domain.com,https://web.telegram.org
POSTGRES_PASSWORD=kuchli_parol
SECRET_KEY=kuchli_jwt_maxfiy_kalit
```

### 3. Docker Compose orqali ishga tushiring:
```bash
docker compose up -d --build
```

Konteynerlar holatini tekshirish:
```bash
docker compose ps
```

Bot loglarini jonli ko‘rish:
```bash
docker compose logs -f bot
```

---

## 🌐 API Endpoints (/api/v1)
* `GET /api/v1/profile/me` — Foydalanuvchi profili, roli, ranki va IStars balansi
* `GET /api/v1/economy/packages` — Playdom to‘lov paketlari (100, 250, 500, 1000 IStars)
* `POST /api/v1/economy/topup` — IStars balansini to‘ldirish
* `GET /api/v1/teams` — Jamoalar ro‘yxati va qidiruv
* `POST /api/v1/teams` — Yangi jamoa tuzish (Pro logo / Custom logo)
* `GET /api/v1/scrims` — 5v5 Scrimlar va avtomatik 30s Ready Check
* `GET /api/v1/pvp/lobbies` — 5v5 PvP Custom lobbilari

---

## 🧪 Testlarni Ishga Tushirish
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 tests/test_platform.py
```
