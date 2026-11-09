from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.core.database import get_db
from app.models.karma import KarmaLog
from app.models.user import User
from app.schemas.karma import (
    KarmaFeedbackCreate,
    KarmaLogResponse,
    KarmaSummaryResponse
)
from app.api.auth import get_current_user

router = APIRouter(prefix="/karma", tags=["Module D: Anti-Troll Karma System"])

ENDORSEMENT_POINTS = {
    "shot_caller": 3,
    "patience": 2,
    "carry": 2,
    "team_player": 2,
    "versatile": 1
}

REPORT_PENALTY_POINTS = {
    "afk": -10,
    "toxicity": -8,
    "intentional_feeding": -12,
    "griefing": -10,
    "false_credentials": -15
}

@router.post("/feedback", response_model=KarmaLogResponse)
async def submit_match_feedback(
    payload: KarmaFeedbackCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submits an Endorsement (+Karma) or Report (-Karma).
    Includes the strict safeguard:
    Reports require at least 3 distinct user reports across distinct matches
    before applying significant Karma deductions to protect against toxic false reporting.
    """
    if payload.target_user_id == current_user.telegram_id:
        raise HTTPException(status_code=400, detail="You cannot endorse or report yourself.")

    target_user = await db.get(User, payload.target_user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="Target player not found.")

    # Prevent duplicate submission for same match and target
    if payload.match_ref_id:
        existing = (await db.execute(
            select(KarmaLog).where(
                KarmaLog.reporter_id == current_user.telegram_id,
                KarmaLog.target_user_id == payload.target_user_id,
                KarmaLog.match_ref_id == payload.match_ref_id
            )
        )).scalars().first()
        if existing:
            raise HTTPException(status_code=400, detail="You have already submitted feedback for this player in this match.")

    if payload.action_type == "endorsement":
        delta = ENDORSEMENT_POINTS.get(payload.tag, 2)
        # Endorsements are credited immediately (capped at 200)
        target_user.karma_score = min(200, target_user.karma_score + delta)
        is_deducted = True
    else:
        # Report
        delta = REPORT_PENALTY_POINTS.get(payload.tag, -10)
        is_deducted = False  # Held in escrow until 3-distinct-report threshold

    log_entry = KarmaLog(
        reporter_id=current_user.telegram_id,
        target_user_id=payload.target_user_id,
        action_type=payload.action_type,
        tag=payload.tag,
        comment=payload.comment,
        points_delta=delta,
        match_ref_type=payload.match_ref_type,
        match_ref_id=payload.match_ref_id,
        is_deducted=is_deducted
    )
    db.add(log_entry)
    await db.flush()

    # 3-REPORT SAFEGUARD EVALUATION
    if payload.action_type == "report":
        # Check undeducted reports from DISTINCT reporters across DISTINCT matches
        distinct_reporters_count = await db.execute(
            select(func.count(func.distinct(KarmaLog.reporter_id))).where(
                KarmaLog.target_user_id == payload.target_user_id,
                KarmaLog.action_type == "report",
                KarmaLog.is_deducted == False
            )
        )
        report_count = distinct_reporters_count.scalar() or 0

        # When 3 or more distinct users report over separate encounters:
        if report_count >= 3:
            unprocessed_reports = (await db.execute(
                select(KarmaLog).where(
                    KarmaLog.target_user_id == payload.target_user_id,
                    KarmaLog.action_type == "report",
                    KarmaLog.is_deducted == False
                )
            )).scalars().all()

            total_penalty = sum(r.points_delta for r in unprocessed_reports)
            target_user.karma_score = max(0, target_user.karma_score + total_penalty)
            target_user.penalties_count += len(unprocessed_reports)

            # Auto-suspend if karma plunges dangerously low (<20)
            if target_user.karma_score < 20:
                target_user.is_banned = True

            for r in unprocessed_reports:
                r.is_deducted = True

    await db.commit()
    await db.refresh(log_entry)
    return log_entry

@router.get("/summary/{user_id}", response_model=KarmaSummaryResponse)
async def get_karma_summary(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Player not found.")

    # Count endorsements and reports
    endorsements = (await db.execute(
        select(KarmaLog.tag, func.count(KarmaLog.id))
        .where(KarmaLog.target_user_id == user_id, KarmaLog.action_type == "endorsement")
        .group_by(KarmaLog.tag)
    )).all()

    total_endorsements = sum(count for _, count in endorsements)
    tag_counts = {tag: count for tag, count in endorsements}

    reports_count = (await db.execute(
        select(func.count(KarmaLog.id))
        .where(KarmaLog.target_user_id == user_id, KarmaLog.action_type == "report")
    )).scalar() or 0

    # Determine Reputation Tier
    tier = "Exemplary"
    if user.karma_score >= 130:
        tier = "Elite Captain"
    elif user.karma_score >= 90:
        tier = "Standard"
    elif user.karma_score >= 50:
        tier = "Warning"
    else:
        tier = "Restricted"

    return KarmaSummaryResponse(
        user_id=user.telegram_id,
        current_score=user.karma_score,
        endorsements_count=total_endorsements,
        reports_count=reports_count,
        reputation_tier=tier,
        top_endorsements=tag_counts
    )

