import asyncio
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.models import Campaign, MessageLog
from app.core.redis import redis_client
from loguru import logger


# --------------------------------------------------
# Campaign eligibility checks
# --------------------------------------------------

def campaign_is_due(campaign: Campaign) -> bool:
    now = datetime.now(timezone.utc)

    if campaign.status != "active":
        return False

    if campaign.start_at and now < campaign.start_at:
        return False

    if campaign.end_at and now > campaign.end_at:
        return False

    return True


def campaign_interval_passed(
    db: Session,
    campaign: Campaign,
) -> bool:
    """
    Checks if enough time has passed since last message.
    """
    last_message = (
        db.query(MessageLog)
        .filter(MessageLog.campaign_id == campaign.id)
        .order_by(MessageLog.sent_at.desc())
        .first()
    )

    if not last_message:
        return True

    delta = datetime.now(timezone.utc) - last_message.sent_at
    return delta.total_seconds() >= campaign.interval_minutes * 60


# --------------------------------------------------
# Redis lock (prevents duplicates)
# --------------------------------------------------

def acquire_campaign_lock(campaign_id: str) -> bool:
    """
    Ensures only one worker processes a campaign at a time.
    """
    key = f"campaign:lock:{campaign_id}"
    return redis_client.set(key, "1", nx=True, ex=120)


def release_campaign_lock(campaign_id: str):
    redis_client.delete(f"campaign:lock:{campaign_id}")


# --------------------------------------------------
# Scheduler loop
# --------------------------------------------------

async def scheduler_loop():
    logger.info("Campaign scheduler started")

    while True:
        db = SessionLocal()

        try:
            campaigns = (
                db.query(Campaign)
                .filter(Campaign.status == "active")
                .all()
            )

            for campaign in campaigns:
                if not campaign_is_due(campaign):
                    continue

                if not campaign_interval_passed(db, campaign):
                    continue

                if not acquire_campaign_lock(str(campaign.id)):
                    continue  # already being processed

                logger.info(f"Enqueuing campaign {campaign.id}")
                asyncio.create_task(run_campaign(campaign.id))

        except Exception:
            logger.exception("Scheduler error")

        finally:
            db.close()

        await asyncio.sleep(30)


# --------------------------------------------------
# Worker delegation
# --------------------------------------------------

async def run_campaign(campaign_id):
    from app.workers.telegram_worker import run_campaign_once

    try:
        await run_campaign_once(campaign_id)
    finally:
        release_campaign_lock(str(campaign_id))
