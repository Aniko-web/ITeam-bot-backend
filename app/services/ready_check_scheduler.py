import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.models.scrim import Scrim, ScrimReadyCheck
from app.models.team import Team, TeamMember
from app.models.user import User
from app.models.karma import KarmaLog
from app.services.telegram_service import telegram_service

logger = logging.getLogger("READY_CHECK_SCHEDULER")

async def run_ready_check_cycle():
    """
    Background worker cycle:
    1. Checks for scheduled scrims within 10 minutes of target_time and auto-triggers Ready Check.
    2. Checks for pending ready checks that exceeded the 5-minute deadline:
       - If fewer than 10 players confirmed: auto-cancel scrim, penalize unready players (-5 Karma).
    """
    async with AsyncSessionLocal() as db:
        now = datetime.utcnow()

        # ----------------------------------------------------------------------
        # 1. AUTO-TRIGGER: Scrims within 10 minutes of target_time
        # ----------------------------------------------------------------------
        ten_mins_ahead = now + timedelta(minutes=10)
        stmt_trigger = select(Scrim).where(
            Scrim.status == "matched",
            Scrim.target_time <= ten_mins_ahead,
            Scrim.target_time > now - timedelta(hours=1)
        )
        scrims_to_trigger = (await db.execute(stmt_trigger)).scalars().all()

        for scrim in scrims_to_trigger:
            try:
                logger.info(f"Auto-triggering Ready Check for Scrim {scrim.id} (10m mark reached).")
                # Fetch 5 starters from host
                host_starters = (await db.execute(
                    select(TeamMember).where(
                        TeamMember.team_id == scrim.host_team_id,
                        TeamMember.status == "active"
                    ).limit(5)
                )).scalars().all()

                # Fetch 5 starters from challenger
                challenger_starters = (await db.execute(
                    select(TeamMember).where(
                        TeamMember.team_id == scrim.challenger_team_id,
                        TeamMember.status == "active"
                    ).limit(5)
                )).scalars().all()

                all_players = host_starters + challenger_starters
                deadline = now + timedelta(seconds=settings.READY_CHECK_WINDOW_SECONDS)

                scrim.status = "ready_check_pending"
                scrim.ready_check_started_at = now
                scrim.ready_check_deadline = deadline

                user_ids = []
                for p in all_players:
                    rc = ScrimReadyCheck(
                        scrim_id=scrim.id,
                        user_id=p.user_id,
                        team_id=p.team_id,
                        is_ready=False,
                        expires_at=deadline
                    )
                    db.add(rc)
                    user_ids.append(p.user_id)

                await db.commit()

                host_team = await db.get(Team, scrim.host_team_id)
                challenger_team = await db.get(Team, scrim.challenger_team_id)

                await telegram_service.broadcast_scrim_ready_check(
                    user_ids=user_ids,
                    scrim_id=scrim.id,
                    match_time_str=scrim.target_time.strftime("%H:%M UTC"),
                    format_str=scrim.format,
                    host_tag=host_team.tag if host_team else "HOST",
                    challenger_tag=challenger_team.tag if challenger_team else "RIVAL"
                )
            except Exception as e:
                logger.error(f"Error auto-triggering ready check for scrim {scrim.id}: {e}")

        # ----------------------------------------------------------------------
        # 2. AUTO-CANCEL & PENALTY: Scrims past the 5-minute deadline
        # ----------------------------------------------------------------------
        stmt_deadline = select(Scrim).where(
            Scrim.status == "ready_check_pending",
            Scrim.ready_check_deadline <= now
        )
        expired_scrims = (await db.execute(stmt_deadline)).scalars().all()

        for scrim in expired_scrims:
            try:
                # Check confirmation count
                checks = (await db.execute(
                    select(ScrimReadyCheck).where(ScrimReadyCheck.scrim_id == scrim.id)
                )).scalars().all()

                ready_count = sum(1 for c in checks if c.is_ready)

                if ready_count < 10:
                    logger.warning(
                        f"Scrim {scrim.id} failed ready check ({ready_count}/10 ready). Auto-cancelling..."
                    )
                    scrim.status = "cancelled"

                    # Penalize players who failed to confirm
                    unready_users = [c.user_id for c in checks if not c.is_ready]
                    for uid in unready_users:
                        user = await db.get(User, uid)
                        if user:
                            user.karma_score = max(0, user.karma_score - settings.PENALTY_KARMA_UNREADY)
                            user.penalties_count += 1
                            log = KarmaLog(
                                reporter_id=0,  # System bot
                                target_user_id=uid,
                                action_type="report",
                                tag="afk",
                                comment=f"Auto-penalty: Failed Scrim Ready Check ({scrim.id})",
                                points_delta=-settings.PENALTY_KARMA_UNREADY,
                                match_ref_type="scrim",
                                match_ref_id=scrim.id,
                                is_deducted=True
                            )
                            db.add(log)

                            # Send Telegram DM penalty notice
                            penalty_notice = (
                                f"⚠️ <b>SCRIM READY CHECK MISSED</b>\n\n"
                                f"You failed to confirm readiness for your scheduled scrim match within 5 minutes.\n"
                                f"A <b>-{settings.PENALTY_KARMA_UNREADY} Karma penalty</b> has been recorded to your trust score."
                            )
                            await telegram_service.send_message(chat_id=uid, text=penalty_notice)

                    await db.commit()

                    # Notify both team captains of cancellation
                    host_team = await db.get(Team, scrim.host_team_id)
                    challenger_team = await db.get(Team, scrim.challenger_team_id) if scrim.challenger_team_id else None

                    cancel_msg = (
                        f"❌ <b>SCRIM CANCELLED: READY CHECK FAILED</b>\n\n"
                        f"Match between <b>{host_team.name if host_team else 'Host'}</b> and "
                        f"<b>{challenger_team.name if challenger_team else 'Rival'}</b> has been auto-cancelled "
                        f"because {10 - ready_count} player(s) did not confirm readiness in time."
                    )
                    if host_team:
                        await telegram_service.send_message(chat_id=host_team.captain_id, text=cancel_msg)
                    if challenger_team:
                        await telegram_service.send_message(chat_id=challenger_team.captain_id, text=cancel_msg)
            except Exception as e:
                logger.error(f"Error handling expired ready check for scrim {scrim.id}: {e}")

async def start_ready_check_scheduler():
    """Starts the non-blocking background loop."""
    logger.info("Ready Check Background Scheduler started.")
    while True:
        try:
            await run_ready_check_cycle()
        except Exception as e:
            logger.error(f"Scheduler loop error: {e}")
        await asyncio.sleep(20)  # Check every 20 seconds

