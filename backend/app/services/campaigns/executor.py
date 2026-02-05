from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from loguru import logger

from app.models.models import (
    Campaign,
    CampaignGroup,
    TelegramGroup,
    TelegramAccount,
)
from app.core.redis import redis_client


# -------------------------
# Helpers
# -------------------------

def campaign_is_due(campaign: Campaign) -> bool:
    now = datetime.utcnow()

    if campaign.status != "active":
        return False

    if campaign.start_at and now < campaign.start_at:
        return False

    if campaign.end_at and now > campaign.end_at:
        return False

    if campaign.last_run_at:
        delta = now - campaign.last_run_at
        return delta.total_seconds() >= campaign.interval_minutes * 60

    return True


def group_cooldown_key(account_id: str, group_id: str) -> str:
    return f"acct:{account_id}:group:{group_id}:last_post"


# -------------------------
# Main selector
# -------------------------

def get_next_campaign_target(
    db: Session,
    account: TelegramAccount,
):
    """
    Returns one eligible campaign + group for this account,
    or None if nothing is safe to send.
    """

    # 1️⃣ Load campaigns for this customer
    campaigns = (
        db.query(Campaign)
        .filter(
            Campaign.customer_id == account.owner_customer_id,
            Campaign.status == "active",
        )
        .order_by(Campaign.created_at.asc())
        .all()
    )

    if not campaigns:
        return None

    now = datetime.utcnow()

    # 2️⃣ Iterate campaigns fairly
    for campaign in campaigns:
        if not campaign_is_due(campaign):
            continue

        # 3️⃣ Load campaign groups
        groups = (
            db.query(TelegramGroup)
            .join(
                CampaignGroup,
                CampaignGroup.group_id == TelegramGroup.id,
            )
            .filter(
                CampaignGroup.campaign_id == campaign.id,
            )
            .all()
        )

        if not groups:
            continue

        # 4️⃣ Find first group not on cooldown
        for group in groups:
            cooldown_key = group_cooldown_key(
                str(account.id),
                str(group.id),
            )

            if redis_client.exists(cooldown_key):
                continue

            # ✅ Eligible target found
            logger.debug(
                f"Selected campaign={campaign.id} "
                f"group={group.telegram_id} "
                f"account={account.phone_number}"
            )

            return {
                "campaign": campaign,
                "group": group,
                "message": campaign.message,  # or template
            }

    # ❌ Nothing eligible
    return None
