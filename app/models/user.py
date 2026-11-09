import datetime
from sqlalchemy import Column, BigInteger, String, Integer, Boolean, DateTime, JSON
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    telegram_id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String(64), nullable=True)
    first_name = Column(String(128), nullable=False)
    last_name = Column(String(128), nullable=True)
    avatar_url = Column(String(512), nullable=True)

    # MLBB In-Game Identity
    mlbb_id = Column(String(32), nullable=False, default="123456789")
    server_id = Column(String(16), nullable=False, default="1001")
    in_game_nickname = Column(String(64), nullable=False, default="MobileLegendPro")

    # Main Roles (Jungler, Mid Laner, Exp Laner, Gold Laner, Roamer)
    main_roles = Column(JSON, default=lambda: ["Jungler", "Mid Laner"])
    # Top 3 Main Heroes
    top_heroes = Column(JSON, default=lambda: ["Fanny", "Ling", "Gusion"])

    # Ranks
    current_rank = Column(String(32), nullable=False, default="Mythic")
    highest_rank = Column(String(32), nullable=False, default="Mythic Glory")
    current_stars = Column(Integer, default=25)

    # Language Preference (uz, ru, en)
    language = Column(String(8), default="uz")

    # Economy & Customization (ITeam Platform)
    istars_balance = Column(Integer, default=0, nullable=False)
    selected_background_id = Column(String(64), default="deep-void", nullable=False)

    # Preferred Playtime & Matchmaking
    playtime_schedule = Column(String(128), default="20:00 - 00:00 UTC+5")
    is_lfg_active = Column(Boolean, default=True, index=True)
    last_lfg_ping = Column(DateTime, default=datetime.datetime.utcnow)

    # Community Trust & Karma
    karma_score = Column(Integer, default=100, index=True)
    total_scrims_played = Column(Integer, default=0)
    total_pvp_played = Column(Integer, default=0)
    penalties_count = Column(Integer, default=0)
    is_banned = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

