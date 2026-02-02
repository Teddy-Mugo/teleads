from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.models import Campaign

router = APIRouter(prefix="/campaigns")


@router.get("/")
def list_campaigns(db: Session = Depends(get_db)):
    return db.query(Campaign).all()


@router.post("/{campaign_id}/pause")
def pause_campaign(campaign_id: str, db: Session = Depends(get_db)):
    campaign = db.get(Campaign, campaign_id)
    campaign.status = "paused"
    db.commit()
    return {"status": "paused"}


@router.post("/{campaign_id}/resume")
def resume_campaign(campaign_id: str, db: Session = Depends(get_db)):
    campaign = db.get(Campaign, campaign_id)
    campaign.status = "active"
    db.commit()
    return {"status": "active"}


@router.post("/{campaign_id}/run")
async def run_campaign(campaign_id: str):
    from app.workers.telegram_worker import run_campaign_once
    await run_campaign_once(campaign_id)
    return {"status": "triggered"}
