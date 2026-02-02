import asyncio
import datetime

from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.models import Campaign


def campaign_is_due(campaign: Campaign) -> bool:
    now = datetime.datetime.utcnow()

    if campaign.status != "active":
        return False

    if campaign.start_at and now < campaign.start_at:
        return False

    if campaign.end_at and now > campaign.end_at:
        return False

    return True


#interval check

def campaign_interval_passed(db: Session, campaign: Campaign) -> bool:
    last_message = (
        db.query(campaign.message_logs)
        .order_by(campaign.message_logs.sent_at.desc())
        .first()
    )

    if not last_message:
        return True

    delta = datetime.datetime.utcnow() - last_message.sent_at
    return delta.total_seconds() >= campaign.interval_minutes * 60


#scheduler loop

async def scheduler_loop():
    while True:
        db = SessionLocal()

        try:
            campaigns = db.query(Campaign).all()

            for campaign in campaigns:
                if not campaign_is_due(campaign):
                    continue

                if not campaign_interval_passed(db, campaign):
                    continue

                # MARK: campaign is due
                await enqueue_campaign(campaign.id)

        finally:
            db.close()

        await asyncio.sleep(30)


#enqueue campaign task

async def enqueue_campaign(campaign_id):
    from app.workers.telegram_worker import run_campaign_once
    await run_campaign_once(campaign_id)

