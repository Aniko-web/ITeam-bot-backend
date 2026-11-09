import uuid
import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, BigInteger, Boolean
from app.core.database import Base

class KarmaLog(Base):
    __tablename__ = "karma_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    reporter_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False)
    target_user_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False, index=True)
    
    action_type = Column(String(16), nullable=False)  # endorsement or report
    tag = Column(String(32), nullable=False)          # shot_caller, patience, carry, afk, toxicity, etc.
    comment = Column(String(256), nullable=True)
    points_delta = Column(Integer, nullable=False)
    
    match_ref_type = Column(String(16), nullable=True)  # scrim, pvp, lfg
    match_ref_id = Column(String(64), nullable=True)
    
    # 3-report safeguard requirement flag
    is_deducted = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

