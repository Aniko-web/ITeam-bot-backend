from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.team import Team, TeamMember
from app.models.user import User
from app.models.transaction import Transaction
from app.schemas.team import (
    TeamCreate,
    TeamUpdate,
    TeamResponse,
    TeamMemberResponse,
    JoinRequestAction
)
from app.api.auth import get_current_user
from app.services.telegram_service import telegram_service

router = APIRouter(prefix="/teams", tags=["Module B: Team Roster & Communication Hub"])

@router.post("/", response_model=TeamResponse)
async def create_team(
    payload: TeamCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if user already owns a team
    existing_captain = await db.execute(select(Team).where(Team.captain_id == current_user.telegram_id))
    if existing_captain.scalars().first():
        raise HTTPException(status_code=400, detail="You already manage a team as captain.")

    # Check name/tag uniqueness
    existing_name = await db.execute(
        select(Team).where((Team.name == payload.name) | (Team.tag == payload.tag))
    )
    if existing_name.scalars().first():
        raise HTTPException(status_code=400, detail="Team name or clan tag is already taken.")

    # ITeam Economy: Validate logo fee (140 IStars for custom, 100 IStars for Pro preset)
    logo_fee = 0
    tx_type = "free"
    if payload.is_custom_logo:
        logo_fee = 140
        tx_type = "team_logo_custom"
    elif payload.pro_team_logo_id:
        logo_fee = 100
        tx_type = "team_logo_pro"

    if logo_fee > 0:
        if current_user.istars_balance < logo_fee:
            raise HTTPException(
                status_code=402,
                detail=f"IStars balansi yetarli emas (kerak: {logo_fee} IStars, mavjud: {current_user.istars_balance}). Playdom orqali to'ldiring."
            )
        current_user.istars_balance -= logo_fee
        db.add(Transaction(
            user_id=current_user.telegram_id,
            amount_istars=-logo_fee,
            amount_uzs=-(logo_fee * 50),
            type=tx_type,
            status="completed",
            provider="internal",
            description=f"Logo fee for team [{payload.tag.upper()}]"
        ))

    team = Team(
        captain_id=current_user.telegram_id,
        name=payload.name,
        tag=payload.tag.upper(),
        description=payload.description,
        voice_type=payload.voice_type,
        voice_link_secret=payload.voice_link_secret,
        max_slots=payload.max_slots,
        min_rank_requirement=payload.min_rank_requirement,
        logo_url=payload.logo_url,
        pro_team_logo_id=payload.pro_team_logo_id,
        is_custom_logo=payload.is_custom_logo,
        is_recruiting=True
    )
    db.add(team)
    await db.flush()

    # Automatically add Captain as active starter
    captain_member = TeamMember(
        team_id=team.id,
        user_id=current_user.telegram_id,
        slot_type="captain",
        assigned_role=current_user.main_roles[0] if current_user.main_roles else "Jungler",
        status="active"
    )
    db.add(captain_member)
    await db.commit()

    return await get_team_detail_internal(team.id, current_user.telegram_id, db)

@router.get("/", response_model=List[TeamResponse])
async def list_recruiting_teams(
    min_rank: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Team).where(Team.is_recruiting == True).order_by(Team.created_at.desc()).offset(offset).limit(limit)
    if min_rank:
        stmt = stmt.where(Team.min_rank_requirement == min_rank)

    result = await db.execute(stmt)
    teams = result.scalars().all()

    output = []
    for t in teams:
        res = await get_team_detail_internal(t.id, current_user.telegram_id, db)
        output.append(res)
    return output

@router.get("/{team_id}", response_model=TeamResponse)
async def get_team_detail(
    team_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await get_team_detail_internal(team_id, current_user.telegram_id, db)

async def get_team_detail_internal(team_id: str, viewer_telegram_id: int, db: AsyncSession) -> TeamResponse:
    team = await db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Fetch members with user details
    stmt = (
        select(TeamMember, User)
        .join(User, TeamMember.user_id == User.telegram_id)
        .where(TeamMember.team_id == team_id)
    )
    rows = (await db.execute(stmt)).all()

    member_responses: List[TeamMemberResponse] = []
    is_active_member = False
    starters = 0
    subs = 0

    for tm, usr in rows:
        if tm.user_id == viewer_telegram_id and tm.status == "active":
            is_active_member = True

        if tm.status == "active":
            if tm.slot_type in ("starter", "captain"):
                starters += 1
            elif tm.slot_type == "substitute":
                subs += 1

        member_responses.append(
            TeamMemberResponse(
                id=tm.id,
                user_id=tm.user_id,
                slot_type=tm.slot_type,
                assigned_role=tm.assigned_role,
                status=tm.status,
                joined_at=tm.joined_at,
                nickname=usr.in_game_nickname,
                rank=usr.current_rank,
                avatar_url=usr.avatar_url,
                karma_score=usr.karma_score
            )
        )

    # STRICT REQUIREMENT: Hide voice channel link unless accepted active member or captain
    revealed_voice_link = team.voice_link_secret if (is_active_member or team.captain_id == viewer_telegram_id) else None

    return TeamResponse(
        id=team.id,
        captain_id=team.captain_id,
        name=team.name,
        tag=team.tag,
        logo_url=team.logo_url,
        pro_team_logo_id=team.pro_team_logo_id,
        is_custom_logo=bool(team.is_custom_logo),
        description=team.description,
        voice_type=team.voice_type,
        voice_link_secret=revealed_voice_link,
        max_slots=team.max_slots,
        is_recruiting=team.is_recruiting,
        min_rank_requirement=team.min_rank_requirement,
        created_at=team.created_at,
        members=member_responses,
        starter_count=starters,
        substitute_count=subs
    )

@router.post("/{team_id}/join-request")
async def request_to_join_team(
    team_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    team = await db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Check if existing member/applicant
    existing = await db.execute(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == current_user.telegram_id)
    )
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="You have already submitted an application or are on the roster.")

    # Check total active roster limit (default 7 slots: 5 starters + 2 subs)
    active_count = await db.execute(
        select(func.count(TeamMember.id)).where(TeamMember.team_id == team_id, TeamMember.status == "active")
    )
    if active_count.scalar() >= team.max_slots:
        raise HTTPException(status_code=400, detail="Team roster is already at full capacity.")

    app = TeamMember(
        team_id=team_id,
        user_id=current_user.telegram_id,
        slot_type="starter",
        assigned_role=current_user.main_roles[0] if current_user.main_roles else "Exp Laner",
        status="pending_approval"
    )
    db.add(app)
    await db.commit()

    # Ping captain via Telegram
    notify_text = (
        f"🛡 <b>New Roster Application!</b>\n\n"
        f"Player <b>{current_user.in_game_nickname}</b> ({current_user.current_rank}) "
        f"has requested to join <b>[{team.tag}] {team.name}</b>.\n"
        f"Role: {', '.join(current_user.main_roles or [])}\n"
        f"Karma Score: 🌟 {current_user.karma_score}"
    )
    await telegram_service.send_message(chat_id=team.captain_id, text=notify_text)

    return {"status": "success", "message": "Application submitted to Team Captain."}

@router.post("/{team_id}/manage-member")
async def manage_team_member(
    team_id: str,
    action_data: JoinRequestAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    team = await db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    if team.captain_id != current_user.telegram_id:
        raise HTTPException(status_code=403, detail="Only team captain can manage roster memberships.")

    member = (await db.execute(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == action_data.target_user_id)
    )).scalars().first()

    if not member:
        raise HTTPException(status_code=404, detail="Roster application/member not found")

    if action_data.action == "accept":
        member.status = "active"
        if action_data.assigned_slot:
            member.slot_type = action_data.assigned_slot
        if action_data.assigned_role:
            member.assigned_role = action_data.assigned_role
        
        # Ping accepted applicant with revealed voice channel notice
        approval_msg = (
            f"🎉 <b>Roster Accepted!</b>\n\n"
            f"You are officially accepted into <b>[{team.tag}] {team.name}</b> as a <b>{member.slot_type.upper()}</b>!\n"
            f"Voice Channel access is now unlocked in your Team Hub."
        )
        await telegram_service.send_message(chat_id=member.user_id, text=approval_msg)

    elif action_data.action == "reject":
        member.status = "declined"
    elif action_data.action == "bench":
        member.slot_type = "substitute"
    elif action_data.action == "promote":
        member.slot_type = "starter"

    await db.commit()
    return {"status": "success", "action": action_data.action}

