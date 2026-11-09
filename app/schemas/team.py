from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class TeamMemberBase(BaseModel):
    user_id: int
    slot_type: str = "starter"  # captain, starter, substitute
    assigned_role: Optional[str] = None
    status: str = "pending_approval"

class TeamMemberResponse(TeamMemberBase):
    id: str
    joined_at: datetime
    nickname: Optional[str] = None
    rank: Optional[str] = None
    avatar_url: Optional[str] = None
    karma_score: Optional[int] = None

    class Config:
        from_attributes = True

class TeamCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=64)
    tag: str = Field(..., min_length=2, max_length=8)
    description: Optional[str] = None
    voice_type: str = Field(default="discord")
    voice_link_secret: Optional[str] = None
    min_rank_requirement: str = Field(default="Mythic")
    max_slots: int = Field(default=7, ge=5, le=12)
    logo_url: Optional[str] = None
    pro_team_logo_id: Optional[str] = None
    is_custom_logo: bool = Field(default=False)

class TeamUpdate(BaseModel):
    name: Optional[str] = None
    tag: Optional[str] = None
    description: Optional[str] = None
    voice_type: Optional[str] = None
    voice_link_secret: Optional[str] = None
    min_rank_requirement: Optional[str] = None
    is_recruiting: Optional[bool] = None
    max_slots: Optional[int] = None
    logo_url: Optional[str] = None
    pro_team_logo_id: Optional[str] = None
    is_custom_logo: Optional[bool] = None

class TeamResponse(BaseModel):
    id: str
    captain_id: int
    name: str
    tag: str
    logo_url: Optional[str] = None
    pro_team_logo_id: Optional[str] = None
    is_custom_logo: bool = False
    description: Optional[str] = None
    voice_type: str
    voice_link_secret: Optional[str] = None  # Populated only if caller is confirmed active member
    max_slots: int
    is_recruiting: bool
    min_rank_requirement: str
    created_at: datetime
    members: List[TeamMemberResponse] = []
    starter_count: int = 0
    substitute_count: int = 0

    class Config:
        from_attributes = True

class JoinRequestAction(BaseModel):
    target_user_id: int
    action: str = Field(..., pattern="^(accept|reject|bench|promote)$")
    assigned_slot: Optional[str] = "starter"  # starter or substitute
    assigned_role: Optional[str] = None

