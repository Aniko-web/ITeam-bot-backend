from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class UserProfileBase(BaseModel):
    mlbb_id: str = Field(..., example="58493012")
    server_id: str = Field(..., example="2048")
    in_game_nickname: str = Field(..., example="ViperGod")
    main_roles: List[str] = Field(default=["Jungler", "Mid Laner"])
    top_heroes: List[str] = Field(default=["Ling", "Fanny", "Hayabusa"])
    current_rank: str = Field(default="Mythic")
    highest_rank: str = Field(default="Mythic Glory")
    current_stars: int = Field(default=35)
    language: str = Field(default="uz", example="uz")
    playtime_schedule: str = Field(default="20:00 - 00:00 UTC+5")
    is_lfg_active: bool = Field(default=True)
    istars_balance: int = Field(default=0, example=250)
    selected_background_id: str = Field(default="deep-void", example="deep-void")

class UserProfileUpdate(BaseModel):
    mlbb_id: Optional[str] = None
    server_id: Optional[str] = None
    in_game_nickname: Optional[str] = None
    main_roles: Optional[List[str]] = None
    top_heroes: Optional[List[str]] = None
    current_rank: Optional[str] = None
    highest_rank: Optional[str] = None
    current_stars: Optional[int] = None
    language: Optional[str] = None
    playtime_schedule: Optional[str] = None
    is_lfg_active: Optional[bool] = None
    selected_background_id: Optional[str] = None

class UserResponse(UserProfileBase):
    telegram_id: int
    username: Optional[str] = None
    first_name: str
    last_name: Optional[str] = None
    avatar_url: Optional[str] = None
    karma_score: int
    total_scrims_played: int
    total_pvp_played: int
    penalties_count: int
    is_banned: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class LFGFilterQuery(BaseModel):
    rank: Optional[str] = None
    role: Optional[str] = None
    min_karma: Optional[int] = 80
    limit: int = 20
    offset: int = 0

