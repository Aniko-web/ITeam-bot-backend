from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.core.database import get_db
from app.models.scrim import Scrim, ScrimReadyCheck
from app.models.team import Team, TeamMember
from app.models.user import User
from app.schemas.scrim import (
    ScrimCreate,
    ScrimAccept,
    ScrimSubmitCredentials,
    ScrimResponse,
    ScrimReadyCheckStatus
)
from app.api.auth import get_current_user
from app.services.telegram_service import telegram_service

router = APIRouter(prefix="/scrims", tags=["Module C: Scrim Finder & Ready Check"])

@router.post("/", response_model=ScrimResponse)
async def create_scrim(
    payload: ScrimCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify user is a team captain
    team = (await db.execute(
        select(Team).where(Team.captain_id == current_user.telegram_id)
    )).scalars().first()
    if not team:
        raise HTTPException(status_code=403, detail="Only team captains can post scrim listings.")

    scrim = Scrim(
        host_team_id=team.id,
        target_time=payload.target_time,
        target_rank=payload.target_rank,
        format=payload.format,
        status="open",
        notes=payload.notes
    )
    db.add(scrim)
    await db.commit()
    return await get_scrim_detail_internal(scrim.id, current_user.telegram_id, db)

@router.get("/", response_model=List[ScrimResponse])
async def list_scrims(
    status_filter: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Scrim).order_by(Scrim.target_time.asc()).offset(offset).limit(limit)
    if status_filter:
        stmt = stmt.where(Scrim.status == status_filter)
    else:
        stmt = stmt.where(Scrim.status.in_(["open", "matched", "ready_check_pending", "ready_check_confirmed"]))

    scrims = (await db.execute(stmt)).scalars().all()
    results = []
    for s in scrims:
        res = await get_scrim_detail_internal(s.id, current_user.telegram_id, db)
        results.append(res)
    return results

@router.post("/{scrim_id}/challenge", response_model=ScrimResponse)
async def challenge_scrim(
    scrim_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    scrim = await db.get(Scrim, scrim_id)
    if not scrim:
        raise HTTPException(status_code=404, detail="Scrim not found")
    if scrim.status != "open":
        raise HTTPException(status_code=400, detail="Scrim is no longer open for challenges.")

    # Find challenger's team
    challenger_team = (await db.execute(
        select(Team).where(Team.captain_id == current_user.telegram_id)
    )).scalars().first()
    if not challenger_team:
        raise HTTPException(status_code=403, detail="You must be a team captain to accept a scrim challenge.")
    if challenger_team.id == scrim.host_team_id:
        raise HTTPException(status_code=400, detail="Cannot challenge your own team's scrim.")

    scrim.challenger_team_id = challenger_team.id
    scrim.status = "matched"
    await db.commit()

    # Notify Host Team Captain
    host_team = await db.get(Team, scrim.host_team_id)
    notify_text = (
        f"⚔️ <b>Scrim Challenge Accepted!</b>\n\n"
        f"Team <b>[{challenger_team.tag}] {challenger_team.name}</b> has accepted your scrim challenge!\n"
        f"📅 Match Time: {scrim.target_time.strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"Format: {scrim.format}\n\n"
        f"Automated 10-player Ready Check will activate 10 minutes prior to match time."
    )
    if host_team:
        await telegram_service.send_message(chat_id=host_team.captain_id, text=notify_text)

    return await get_scrim_detail_internal(scrim.id, current_user.telegram_id, db)

@router.post("/{scrim_id}/trigger-ready-check")
async def trigger_ready_check(
    scrim_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Automated Ready Check System:
    Triggers 10 minutes before scheduled match time (or on-demand by captain).
    Pings all 10 players across both rosters with inline Ready confirmation.
    """
    scrim = await db.get(Scrim, scrim_id)
    if not scrim:
        raise HTTPException(status_code=404, detail="Scrim not found")
    if not scrim.challenger_team_id:
        raise HTTPException(status_code=400, detail="Cannot trigger ready check without rival team.")

    # Fetch top 5 active starters for Host team
    host_members = (await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == scrim.host_team_id,
            TeamMember.status == "active"
        ).limit(5)
    )).scalars().all()

    # Fetch top 5 active starters for Challenger team
    challenger_members = (await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == scrim.challenger_team_id,
            TeamMember.status == "active"
        ).limit(5)
    )).scalars().all()

    all_players = host_members + challenger_members
    now = datetime.utcnow()
    deadline = now + timedelta(minutes=5)

    scrim.status = "ready_check_pending"
    scrim.ready_check_started_at = now
    scrim.ready_check_deadline = deadline

    # Clear prior ready checks if any
    prior_checks = (await db.execute(
        select(ScrimReadyCheck).where(ScrimReadyCheck.scrim_id == scrim_id)
    )).scalars().all()
    for pc in prior_checks:
        await db.delete(pc)

    # Initialize 10 ready check records
    user_ids_to_notify = []
    for member in all_players:
        rc = ScrimReadyCheck(
            scrim_id=scrim.id,
            user_id=member.user_id,
            team_id=member.team_id,
            is_ready=False,
            expires_at=deadline
        )
        db.add(rc)
        user_ids_to_notify.append(member.user_id)

    await db.commit()

    # Broadcast inline ready check button to all 10 players
    host_team = await db.get(Team, scrim.host_team_id)
    challenger_team = await db.get(Team, scrim.challenger_team_id)
    await telegram_service.broadcast_scrim_ready_check(
        user_ids=user_ids_to_notify,
        scrim_id=scrim.id,
        match_time_str=scrim.target_time.strftime("%H:%M UTC"),
        format_str=scrim.format,
        host_tag=host_team.tag if host_team else "HOST",
        challenger_tag=challenger_team.tag if challenger_team else "RIVAL"
    )

    return {"status": "success", "message": "Ready check countdown started for 10 players."}

@router.post("/{scrim_id}/confirm-ready")
async def confirm_player_ready(
    scrim_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    scrim = await db.get(Scrim, scrim_id)
    if not scrim:
        raise HTTPException(status_code=404, detail="Scrim not found")
    if scrim.status != "ready_check_pending":
        raise HTTPException(status_code=400, detail="Ready check is not currently pending.")

    # Find user's ready check entry
    rc = (await db.execute(
        select(ScrimReadyCheck).where(
            ScrimReadyCheck.scrim_id == scrim_id,
            ScrimReadyCheck.user_id == current_user.telegram_id
        )
    )).scalars().first()

    if not rc:
        raise HTTPException(status_code=403, detail="You are not in the starting 10 lineup for this match.")

    rc.is_ready = True
    rc.confirmed_at = datetime.utcnow()
    await db.commit()

    # Check if all 10 have confirmed
    all_rcs = (await db.execute(
        select(ScrimReadyCheck).where(ScrimReadyCheck.scrim_id == scrim_id)
    )).scalars().all()

    ready_count = sum(1 for r in all_rcs if r.is_ready)
    if ready_count >= 10:
        scrim.status = "ready_check_confirmed"
        await db.commit()

        # Prompt Host Captain to enter custom Room ID & Password
        host_team = await db.get(Team, scrim.host_team_id)
        if host_team:
            prompt_text = (
                f"🌟 <b>ALL 10 PLAYERS CONFIRMED READY!</b>\n\n"
                f"Captain, please open the Mini App and submit the MLBB Custom Room ID and Password "
                f"so all players can join."
            )
            await telegram_service.send_message(chat_id=host_team.captain_id, text=prompt_text)

    return {"status": "success", "ready_count": ready_count, "total_required": len(all_rcs)}

@router.post("/{scrim_id}/credentials")
async def submit_room_credentials(
    scrim_id: str,
    creds: ScrimSubmitCredentials,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    scrim = await db.get(Scrim, scrim_id)
    if not scrim:
        raise HTTPException(status_code=404, detail="Scrim not found")
    
    host_team = await db.get(Team, scrim.host_team_id)
    if not host_team or host_team.captain_id != current_user.telegram_id:
        raise HTTPException(status_code=403, detail="Only host team captain can submit room credentials.")

    if scrim.status != "ready_check_confirmed":
        raise HTTPException(status_code=400, detail="All 10 players must confirm ready check first.")

    scrim.custom_room_id = creds.custom_room_id
    scrim.custom_room_password = creds.custom_room_password
    scrim.status = "in_progress"
    await db.commit()

    # Get all 10 players
    all_rcs = (await db.execute(
        select(ScrimReadyCheck).where(ScrimReadyCheck.scrim_id == scrim_id)
    )).scalars().all()
    recipient_ids = [r.user_id for r in all_rcs]

    challenger_team = await db.get(Team, scrim.challenger_team_id)
    match_title = f"{host_team.tag} vs {challenger_team.tag if challenger_team else 'RIVAL'} ({scrim.format})"

    # Broadcast Room ID and Password immediately to all players
    await telegram_service.broadcast_room_credentials(
        user_ids=recipient_ids,
        room_id=creds.custom_room_id,
        password=creds.custom_room_password,
        match_title=match_title
    )

    return {"status": "success", "message": "Credentials broadcast to all 10 participants."}

@router.get("/{scrim_id}", response_model=ScrimResponse)
async def get_scrim_detail(
    scrim_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await get_scrim_detail_internal(scrim_id, current_user.telegram_id, db)

async def get_scrim_detail_internal(scrim_id: str, viewer_id: int, db: AsyncSession) -> ScrimResponse:
    scrim = await db.get(Scrim, scrim_id)
    if not scrim:
        raise HTTPException(status_code=404, detail="Scrim not found")

    host_team = await db.get(Team, scrim.host_team_id)
    challenger_team = await db.get(Team, scrim.challenger_team_id) if scrim.challenger_team_id else None

    # Fetch ready checks
    rc_stmt = (
        select(ScrimReadyCheck, User)
        .join(User, ScrimReadyCheck.user_id == User.telegram_id)
        .where(ScrimReadyCheck.scrim_id == scrim_id)
    )
    rc_rows = (await db.execute(rc_stmt)).all()

    ready_checks: List[ScrimReadyCheckStatus] = []
    total_confirmed = 0
    is_participant = False

    for rc, usr in rc_rows:
        if rc.user_id == viewer_id:
            is_participant = True
        if rc.is_ready:
            total_confirmed += 1
        ready_checks.append(
            ScrimReadyCheckStatus(
                user_id=rc.user_id,
                nickname=usr.in_game_nickname,
                team_id=rc.team_id,
                is_ready=rc.is_ready,
                confirmed_at=rc.confirmed_at
            )
        )

    # Room ID/Password only visible if match is in progress / credentials shared AND user is a participant or captain
    is_captain = (host_team and host_team.captain_id == viewer_id) or (challenger_team and challenger_team.captain_id == viewer_id)
    can_view_creds = (scrim.status in ["ready_check_confirmed", "in_progress"]) and (is_participant or is_captain)

    return ScrimResponse(
        id=scrim.id,
        host_team_id=scrim.host_team_id,
        host_team_name=host_team.name if host_team else None,
        host_team_tag=host_team.tag if host_team else None,
        challenger_team_id=scrim.challenger_team_id,
        challenger_team_name=challenger_team.name if challenger_team else None,
        challenger_team_tag=challenger_team.tag if challenger_team else None,
        target_time=scrim.target_time,
        target_rank=scrim.target_rank,
        format=scrim.format,
        status=scrim.status,
        custom_room_id=scrim.custom_room_id if can_view_creds else None,
        custom_room_password=scrim.custom_room_password if can_view_creds else None,
        ready_check_started_at=scrim.ready_check_started_at,
        ready_check_deadline=scrim.ready_check_deadline,
        ready_checks=ready_checks,
        total_confirmed=total_confirmed,
        total_required=10,
        notes=scrim.notes,
        created_at=scrim.created_at
    )

