from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.user import User
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionResponse, TopUpRequest
from app.api.auth import get_current_user

router = APIRouter(prefix="/economy", tags=["ITeam Economy & Playdom Partner"])

PACKAGES: Dict[str, Dict[str, Any]] = {
    "pkg_100": {
        "id": "pkg_100",
        "name": "Starter Stash",
        "istars": 100,
        "uzs": 5000,
        "bonus": 0,
        "is_popular": False,
        "description": "Pro Team Logosi uchun yetarli (5,000 UZS)"
    },
    "pkg_250": {
        "id": "pkg_250",
        "name": "Custom Team Pack",
        "istars": 250,
        "uzs": 12500,
        "bonus": 10,
        "is_popular": True,
        "description": "Custom Logo (140 IStars) + Zaxira IStars"
    },
    "pkg_500": {
        "id": "pkg_500",
        "name": "Captain Bundle",
        "istars": 500,
        "uzs": 25000,
        "bonus": 35,
        "is_popular": False,
        "description": "Jamoa brendingi va premium musobaqa badallari"
    },
    "pkg_1000": {
        "id": "pkg_1000",
        "name": "Esports Organization",
        "istars": 1000,
        "uzs": 50000,
        "bonus": 100,
        "is_popular": False,
        "description": "Eng yuqori bonus va barcha moslashtirishlar"
    }
}

@router.get("/packages")
async def list_packages():
    """List available IStars top-up packages through Playdom."""
    return {
        "rate": "100 IStars = 5,000 UZS (1 IStar = 50 UZS)",
        "packages": list(PACKAGES.values()),
        "pro_team_logo_fee": 100,
        "custom_team_logo_fee": 140
    }

@router.get("/balance")
async def get_balance(
    current_user: User = Depends(get_current_user)
):
    """Retrieve user's IStars balance and exchange rates."""
    return {
        "istars_balance": current_user.istars_balance,
        "uzs_equivalent": current_user.istars_balance * 50,
        "telegram_id": current_user.telegram_id,
        "rates": {
            "pro_team_logo": 100,
            "custom_team_logo": 140,
            "istars_per_uzs": 0.02
        }
    }

@router.get("/transactions", response_model=List[TransactionResponse])
async def list_user_transactions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List historical transaction records for current user."""
    stmt = (
        select(Transaction)
        .where(Transaction.user_id == current_user.telegram_id)
        .order_by(Transaction.created_at.desc())
        .limit(50)
    )
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/topup", response_model=Dict[str, Any])
async def playdom_topup(
    payload: TopUpRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fulfilled via partner service 'Playdom'.
    Deposits purchased IStars into user's balance and records transaction.
    """
    pkg = PACKAGES.get(payload.package_id)
    if not pkg:
        raise HTTPException(status_code=400, detail="Invalid package ID")

    istars_to_credit = pkg["istars"] + pkg["bonus"]
    uzs_amount = pkg["uzs"]

    # Credit balance
    current_user.istars_balance += istars_to_credit

    # Create transaction log
    tx = Transaction(
        user_id=current_user.telegram_id,
        amount_istars=istars_to_credit,
        amount_uzs=uzs_amount,
        type="topup",
        status="completed",
        provider="playdom",
        description=f"Playdom Top-up: {pkg['name']} (+{istars_to_credit} IStars)"
    )
    db.add(tx)
    await db.commit()
    await db.refresh(current_user)

    return {
        "success": True,
        "message": f"Muvaffaqiyatli to'ldirildi! +{istars_to_credit} IStars hisobingizga qo'shildi.",
        "new_balance": current_user.istars_balance,
        "credited_istars": istars_to_credit,
        "amount_uzs": uzs_amount,
        "provider": "playdom",
        "transaction_id": tx.id
    }

