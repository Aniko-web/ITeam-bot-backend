from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class PvPParticipantResponse(BaseModel):
    id: str
    user_id: int
    nickname: str
    rank: str
    avatar_url: Optional[str] = None
    slot_index: int
    team_side: str
    selected_role: str
    is_ready: bool
    joined_at: datetime

    class Config:
        from_attributes = True

class PvPLobbyCreate(BaseModel):
    title: str = Field(default="Community 5v5 Custom Battle")
    format: str = Field(default="BO1")
    target_rank: str = Field(default="Mythic")

class PvPLobbyResponse(BaseModel):
    id: str
    lobby_code: str
    title: str
    creator_telegram_id: int
    format: str
    target_rank: str
    max_slots: int
    status: str
    custom_room_id: Optional[str] = None
    custom_room_password: Optional[str] = None
    participants: List[PvPParticipantResponse] = []
    blue_team: List[PvPParticipantResponse] = []
    red_team: List[PvPParticipantResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True

class JoinPvPLobbyRequest(BaseModel):
    slot_index: int = Field(..., ge=0, le=9)
    selected_role: str = Field(..., example="Jungler")

class SubmitPvPCredentials(BaseModel):
    custom_room_id: str
    custom_room_password: str

