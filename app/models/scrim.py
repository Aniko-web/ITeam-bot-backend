import uuid
import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, BigInteger, Boolean
from app.core.database import Base

class Scrim(Base):
    __tablename__ = "scrims"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    host_team_id = Column(String(36), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    challenger_team_id = Column(String(36), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True)

    target_time = Column(DateTime, nullable=False, index=True)
    target_rank = Column(String(32), default="Mythic")
    format = Column(String(8), default="BO3")  # BO1, BO3, BO5
    status = Column(String(32), default="open", index=True)
    # open -> matched -> ready_check_pending -> ready_check_confirmed -> completed / cancelled

    # Custom Room Credentials (revealed only once all 10 players confirm ready)
    custom_room_id = Column(String(64), nullable=True)
    custom_room_password = Column(String(64), nullable=True)

    ready_check_started_at = Column(DateTime, nullable=True)
    ready_check_deadline = Column(DateTime, nullable=True)

    notes = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class ScrimReadyCheck(Base):
    __tablename__ = "scrim_ready_checks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scrim_id = Column(String(36), ForeignKey("scrims.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False)
    team_id = Column(String(36), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)

    is_ready = Column(Boolean, default=False)
    confirmed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)

