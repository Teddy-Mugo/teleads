from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.models import MessageLog, Campaign
from .router import customer_auth

router = APIRouter(prefix="/logs")


@router.get("/")
def campaign_logs(
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

    return (
        db.query(MessageLog)
        .filter(MessageLog.campaign_id == campaign.id)
        .order_by(MessageLog.sent_at.desc())
        .limit(200)
        .all()
    )
