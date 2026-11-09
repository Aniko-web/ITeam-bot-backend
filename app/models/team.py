import uuid
import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from app.core.database import Base

class Team(Base):
    __tablename__ = "teams"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    captain_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="RESTRICT"), nullable=False, index=True)
    name = Column(String(64), nullable=False, unique=True)
    tag = Column(String(8), nullable=False, unique=True)
    logo_url = Column(String(512), nullable=True)
    pro_team_logo_id = Column(String(64), nullable=True)
    is_custom_logo = Column(Boolean, default=False, nullable=False)
    description = Column(String(512), nullable=True)

    # Voice Comms & Strict Privacy Shield
    voice_type = Column(String(32), default="discord")  # in_game_mic, telegram_voice, discord, other
    voice_link_secret = Column(String(256), nullable=True)  # STRICTLY HIDDEN UNTIL ACCEPTED

    # Roster Capacity (Default: 5 Starter + 2 Subs = 7. Upgradable to 12)
    max_slots = Column(Integer, default=7)
    is_recruiting = Column(Boolean, default=True, index=True)
    min_rank_requirement = Column(String(32), default="Mythic")

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")


class TeamMember(Base):
    __tablename__ = "team_members"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    team_id = Column(String(36), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False, index=True)
    
    slot_type = Column(String(20), default="starter")  # captain, starter, substitute
    assigned_role = Column(String(32), nullable=True)   # Jungler, Mid Laner, Exp Laner, Gold Laner, Roamer
    status = Column(String(20), default="pending_approval")  # active, pending_approval, benched, declined
    joined_at = Column(DateTime, default=datetime.datetime.utcnow)

    team = relationship("Team", back_populates="members")

