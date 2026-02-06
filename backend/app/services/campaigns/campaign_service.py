from sqlalchemy.orm import Session

from app.models.models import Campaign, Customer, MarketList
from app.services.pricing.enforcement import validate_campaign_against_plan


def create_campaign(
    db: Session,
    customer: Customer,
    data,
) -> Campaign:
    campaign = Campaign(
        customer_id=customer.id,
        name=data.name,
        message=data.message,
        interval_minutes=data.interval_minutes,
        start_at=data.start_at,
        end_at=data.end_at,
        status="active",
    )

    # 🔒 PRICING ENFORCEMENT (CORRECT LOCATION)
    validate_campaign_against_plan(
        campaign=campaign,
        plan_name=customer.subscription_tier,
    )

    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    return campaign


def update_campaign(
    db: Session,
    campaign: Campaign,
    customer: Customer,
    updates: dict,
) -> Campaign:
    for key, value in updates.items():
        setattr(campaign, key, value)

    validate_campaign_against_plan(
        campaign=campaign,
        plan_name=customer.subscription_tier,
    )

    db.commit()
    db.refresh(campaign)

    return campaign

def attach_market_lists_to_campaign(
    *,
    db: Session,
    campaign,
    market_list_ids: list,
    customer_id,
):
    lists = (
        db.query(MarketList)
        .filter(
            MarketList.id.in_(market_list_ids),
            MarketList.customer_id == customer_id,
        )
        .all()
    )

    if not lists:
        raise ValueError("No valid market lists selected")

    campaign.market_lists = lists
    db.commit()
