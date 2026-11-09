from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class TransactionResponse(BaseModel):
    id: str
    user_id: int
    amount_istars: int
    amount_uzs: int
    type: str
    status: str
    provider: str
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class TopUpRequest(BaseModel):
    package_id: str = Field(..., example="pkg_100")  # pkg_100, pkg_250, pkg_500, pkg_1000
    telegram_id: Optional[int] = None

