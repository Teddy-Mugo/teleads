# app/services/pricing/enforcement.py

from app.services.pricing.plans import get_plan
from app.models.models import Campaign, TelegramAccount


def validate_campaign_against_plan(
    campaign: Campaign,
    plan_name: str,
):
    plan = get_plan(plan_name)

    if campaign.interval_minutes < plan.min_interval_minutes:
        raise ValueError(
            f"Your plan requires a minimum interval of "
            f"{plan.min_interval_minutes} minutes"
        )


def apply_plan_to_account(
    account: TelegramAccount,
    plan_name: str,
):
    plan = get_plan(plan_name)
    account.daily_message_limit = plan.daily_messages_per_account
