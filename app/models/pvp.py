import uuid
import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, BigInteger, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base

class PvPLobby(Base):
    __tablename__ = "pvp_lobbies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lobby_code = Column(String(16), unique=True, nullable=False, index=True)
    title = Column(String(128), default="Community 5v5 Custom Battle")
    creator_telegram_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False)
    telegram_chat_id = Column(BigInteger, nullable=True)

    format = Column(String(8), default="BO1")
    target_rank = Column(String(32), default="Mythic")
    max_slots = Column(Integer, default=10)
    status = Column(String(32), default="open", index=True)  # open, full, ready, credentials_shared, completed, cancelled

    custom_room_id = Column(String(64), nullable=True)
    custom_room_password = Column(String(64), nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    participants = relationship("PvPParticipant", back_populates="lobby", cascade="all, delete-orphan")


class PvPParticipant(Base):
    __tablename__ = "pvp_participants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lobby_id = Column(String(36), ForeignKey("pvp_lobbies.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False)
    
    slot_index = Column(Integer, nullable=False)  # 0 to 9 (0-4 Blue, 5-9 Red)
    team_side = Column(String(4), nullable=False)   # BLUE or RED
    selected_role = Column(String(32), default="Exp Laner")
    is_ready = Column(Boolean, default=False)
    joined_at = Column(DateTime, default=datetime.datetime.utcnow)

    lobby = relationship("PvPLobby", back_populates="participants")

