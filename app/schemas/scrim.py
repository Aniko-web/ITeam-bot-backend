from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class ScrimCreate(BaseModel):
    target_time: datetime
    target_rank: str = Field(default="Mythic")
    format: str = Field(default="BO3")
    notes: Optional[str] = None

class ScrimAccept(BaseModel):
    challenger_team_id: str

class ScrimSubmitCredentials(BaseModel):
    custom_room_id: str = Field(..., min_length=3)
    custom_room_password: str = Field(..., min_length=2)

class ScrimReadyCheckStatus(BaseModel):
    user_id: int
    nickname: str
    team_id: str
    is_ready: bool
    confirmed_at: Optional[datetime] = None

class ScrimResponse(BaseModel):
    id: str
    host_team_id: str
    host_team_name: Optional[str] = None
    host_team_tag: Optional[str] = None
    challenger_team_id: Optional[str] = None
    challenger_team_name: Optional[str] = None
    challenger_team_tag: Optional[str] = None
    target_time: datetime
    target_rank: str
    format: str
    status: str
    custom_room_id: Optional[str] = None
    custom_room_password: Optional[str] = None
    ready_check_started_at: Optional[datetime] = None
    ready_check_deadline: Optional[datetime] = None
    ready_checks: List[ScrimReadyCheckStatus] = []
    total_confirmed: int = 0
    total_required: int = 10
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

