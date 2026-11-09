from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class KarmaFeedbackCreate(BaseModel):
    target_user_id: int
    action_type: str = Field(..., pattern="^(endorsement|report)$")
    tag: str = Field(..., example="shot_caller")
    comment: Optional[str] = Field(None, max_length=256)
    match_ref_type: Optional[str] = "scrim"  # scrim, pvp, lfg
    match_ref_id: Optional[str] = None

class KarmaLogResponse(BaseModel):
    id: str
    reporter_id: int
    target_user_id: int
    action_type: str
    tag: str
    comment: Optional[str] = None
    points_delta: int
    match_ref_type: Optional[str] = None
    match_ref_id: Optional[str] = None
    is_deducted: bool
    created_at: datetime

    class Config:
        from_attributes = True

class KarmaSummaryResponse(BaseModel):
    user_id: int
    current_score: int
    endorsements_count: int
    reports_count: int
    reputation_tier: str  # "Elite Captain", "Exemplary", "Standard", "Warning", "Restricted"
    top_endorsements: dict[str, int]

