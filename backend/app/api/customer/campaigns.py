from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.db import get_db
from app.models.models import Campaign, CampaignGroup
from .router import customer_auth

router = APIRouter(prefix="/campaigns")


@router.post("/")
def create_campaign(
    payload: dict,
    customer=Depends(customer_auth),
    db: Session = Depends(get_db),
):
    campaign = Campaign(
        customer_id=customer.id,
        name=payload["name"],
        campaign_type=payload["campaign_type"],  # shared | dedicated
        message_template=payload["message"],
        interval_minutes=payload["interval_minutes"],
        start_at=datetime.fromisoformat(payload["start_at"])
        if payload.get("start_at") else None,
        end_at=datetime.fromisoformat(payload["end_at"])
        if payload.get("end_at") else None,
        status="draft",
    )

    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    # attach groups
    for group_id in payload.get("group_ids", []):
        db.add(CampaignGroup(
            campaign_id=campaign.id,
            group_id=group_id,
        ))

    db.commit()

    return {"id": campaign.id, "status": campaign.status}


#list campaigns
@router.get("/")
def list_campaigns(
    customer=Depends(customer_auth),
    db: Session = Depends(get_db),
):
    return (
        db.query(Campaign)
        .filter(Campaign.customer_id == customer.id)
        .all()
    )


#update campaigns
@router.put("/{campaign_id}")
def update_campaign(
    campaign_id: str,
    payload: dict,
    customer=Depends(customer_auth),
    db: Session = Depends(get_db),
):
    campaign = (
        db.query(Campaign)
        .filter(
            Campaign.id == campaign_id,
            Campaign.customer_id == customer.id,
        )
        .first()
    )

    campaign.name = payload.get("name", campaign.name)
    campaign.message_template = payload.get(
        "message", campaign.message_template
    )
    campaign.interval_minutes = payload.get(
        "interval_minutes", campaign.interval_minutes
    )

    db.commit()
    return {"status": "updated"}


#start and stop campaigns   
@router.post("/{campaign_id}/start")
def start_campaign(
    campaign_id: str,
    customer=Depends(customer_auth),
    db: Session = Depends(get_db),
):
    campaign = (
        db.query(Campaign)
        .filter(
            Campaign.id == campaign_id,
            Campaign.customer_id == customer.id,
        )
        .first()
    )
    campaign.status = "active"
    db.commit()
    return {"status": "active"}


@router.post("/{campaign_id}/pause")
def pause_campaign(
    campaign_id: str,
    customer=Depends(customer_auth),
    db: Session = Depends(get_db),
):
    campaign = (
        db.query(Campaign)
        .filter(
            Campaign.id == campaign_id,
            Campaign.customer_id == customer.id,
        )
        .first()
    )
    campaign.status = "paused"
    db.commit()
    return {"status": "paused"}

