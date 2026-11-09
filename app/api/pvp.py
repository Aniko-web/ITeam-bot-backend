import secrets
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.models.pvp import PvPLobby, PvPParticipant
from app.models.user import User
from app.schemas.pvp import (
    PvPLobbyCreate,
    PvPLobbyResponse,
    PvPParticipantResponse,
    JoinPvPLobbyRequest,
    SubmitPvPCredentials
)
from app.api.auth import get_current_user
from app.services.telegram_service import telegram_service

router = APIRouter(prefix="/pvp", tags=["Module E: Admin Community PvP Lobby"])

def generate_lobby_code() -> str:
    return secrets.token_hex(3).upper()  # e.g., 'E8A1B2'

@router.post("/create", response_model=PvPLobbyResponse)
async def create_pvp_lobby(
    payload: PvPLobbyCreate,
    telegram_chat_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    code = generate_lobby_code()
    lobby = PvPLobby(
        lobby_code=code,
        title=payload.title,
        creator_telegram_id=current_user.telegram_id,
        telegram_chat_id=telegram_chat_id,
        format=payload.format,
        target_rank=payload.target_rank,
        max_slots=10,
        status="open"
    )
    db.add(lobby)
    await db.commit()
    return await get_pvp_lobby_internal(lobby.id, current_user.telegram_id, db)

@router.get("/code/{lobby_code}", response_model=PvPLobbyResponse)
async def get_lobby_by_code(
    lobby_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    lobby = (await db.execute(
        select(PvPLobby).where(PvPLobby.lobby_code == lobby_code.upper())
    )).scalars().first()

    if not lobby:
        raise HTTPException(status_code=404, detail="PvP Lobby not found with code " + lobby_code)
    return await get_pvp_lobby_internal(lobby.id, current_user.telegram_id, db)

@router.post("/{lobby_id}/join-slot", response_model=PvPLobbyResponse)
async def join_pvp_slot(
    lobby_id: str,
    req: JoinPvPLobbyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    lobby = await db.get(PvPLobby, lobby_id)
    if not lobby:
        raise HTTPException(status_code=404, detail="PvP Lobby not found")
    if lobby.status not in ["open", "full"]:
        raise HTTPException(status_code=400, detail="Lobby is closed.")

    # Check if slot already taken
    existing_slot = (await db.execute(
        select(PvPParticipant).where(
            PvPParticipant.lobby_id == lobby_id,
            PvPParticipant.slot_index == req.slot_index
        )
    )).scalars().first()
    if existing_slot:
        raise HTTPException(status_code=400, detail="Slot is already occupied.")

    # Remove user from any other slot in this lobby if already joined
    prior_slot = (await db.execute(
        select(PvPParticipant).where(
            PvPParticipant.lobby_id == lobby_id,
            PvPParticipant.user_id == current_user.telegram_id
        )
    )).scalars().first()
    if prior_slot:
        await db.delete(prior_slot)

    # 0..4 = BLUE team, 5..9 = RED team
    team_side = "BLUE" if req.slot_index < 5 else "RED"

    participant = PvPParticipant(
        lobby_id=lobby_id,
        user_id=current_user.telegram_id,
        slot_index=req.slot_index,
        team_side=team_side,
        selected_role=req.selected_role,
        is_ready=True
    )
    db.add(participant)
    await db.flush()

    # Check total count
    all_participants = (await db.execute(
        select(PvPParticipant).where(PvPParticipant.lobby_id == lobby_id)
    )).scalars().all()

    if len(all_participants) >= 10:
        lobby.status = "full"
        # Notify host that all 10 slots are filled
        admin_text = (
            f"🔥 <b>Community PvP Lobby '{lobby.title}' is FULL (10/10)!</b>\n\n"
            f"Host, please open the Mini App and reveal the Custom Room ID & Password."
        )
        await telegram_service.send_message(chat_id=lobby.creator_telegram_id, text=admin_text)

    await db.commit()
    return await get_pvp_lobby_internal(lobby.id, current_user.telegram_id, db)

@router.post("/{lobby_id}/leave-slot", response_model=PvPLobbyResponse)
async def leave_pvp_slot(
    lobby_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    participant = (await db.execute(
        select(PvPParticipant).where(
            PvPParticipant.lobby_id == lobby_id,
            PvPParticipant.user_id == current_user.telegram_id
        )
    )).scalars().first()

    if participant:
        await db.delete(participant)
        lobby = await db.get(PvPLobby, lobby_id)
        if lobby and lobby.status == "full":
            lobby.status = "open"
        await db.commit()

    return await get_pvp_lobby_internal(lobby_id, current_user.telegram_id, db)

@router.post("/{lobby_id}/reveal-credentials")
async def reveal_pvp_credentials(
    lobby_id: str,
    creds: SubmitPvPCredentials,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    lobby = await db.get(PvPLobby, lobby_id)
    if not lobby:
        raise HTTPException(status_code=404, detail="PvP Lobby not found")
    if lobby.creator_telegram_id != current_user.telegram_id:
        raise HTTPException(status_code=403, detail="Only lobby host can submit custom room credentials.")

    lobby.custom_room_id = creds.custom_room_id
    lobby.custom_room_password = creds.custom_room_password
    lobby.status = "credentials_shared"
    await db.commit()

    # Broadcast to all 10 participants
    participants = (await db.execute(
        select(PvPParticipant).where(PvPParticipant.lobby_id == lobby_id)
    )).scalars().all()

    recipient_ids = [p.user_id for p in participants]
    await telegram_service.broadcast_room_credentials(
        user_ids=recipient_ids,
        room_id=creds.custom_room_id,
        password=creds.custom_room_password,
        match_title=lobby.title
    )

    return {"status": "success", "message": "Room credentials broadcast to all lobby participants."}

async def get_pvp_lobby_internal(lobby_id: str, viewer_id: int, db: AsyncSession) -> PvPLobbyResponse:
    lobby = await db.get(PvPLobby, lobby_id)
    if not lobby:
        raise HTTPException(status_code=404, detail="Lobby not found")

    stmt = (
        select(PvPParticipant, User)
        .join(User, PvPParticipant.user_id == User.telegram_id)
        .where(PvPParticipant.lobby_id == lobby_id)
        .order_by(PvPParticipant.slot_index.asc())
    )
    rows = (await db.execute(stmt)).all()

    all_part: List[PvPParticipantResponse] = []
    blue: List[PvPParticipantResponse] = []
    red: List[PvPParticipantResponse] = []
    is_in_lobby = False

    for part, usr in rows:
        if part.user_id == viewer_id:
            is_in_lobby = True
        item = PvPParticipantResponse(
            id=part.id,
            user_id=part.user_id,
            nickname=usr.in_game_nickname,
            rank=usr.current_rank,
            avatar_url=usr.avatar_url,
            slot_index=part.slot_index,
            team_side=part.team_side,
            selected_role=part.selected_role,
            is_ready=part.is_ready,
            joined_at=part.joined_at
        )
        all_part.append(item)
        if part.team_side == "BLUE":
            blue.append(item)
        else:
            red.append(item)

    is_host = lobby.creator_telegram_id == viewer_id
    can_view_creds = (lobby.status in ["credentials_shared", "in_progress"]) and (is_in_lobby or is_host)

    return PvPLobbyResponse(
        id=lobby.id,
        lobby_code=lobby.lobby_code,
        title=lobby.title,
        creator_telegram_id=lobby.creator_telegram_id,
        format=lobby.format,
        target_rank=lobby.target_rank,
        max_slots=lobby.max_slots,
        status=lobby.status,
        custom_room_id=lobby.custom_room_id if can_view_creds else None,
        custom_room_password=lobby.custom_room_password if can_view_creds else None,
        participants=all_part,
        blue_team=blue,
        red_team=red,
        created_at=lobby.created_at
    )

