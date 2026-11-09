import uuid
import datetime
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, ForeignKey, Text
from app.core.database import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False, index=True)
    amount_istars = Column(Integer, nullable=False)
    amount_uzs = Column(BigInteger, nullable=False, default=0)
    type = Column(String(32), nullable=False)  # "topup", "team_logo_pro", "team_logo_custom"
    status = Column(String(32), default="completed", nullable=False)
    provider = Column(String(32), default="playdom", nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

