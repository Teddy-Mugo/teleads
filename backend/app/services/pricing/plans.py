# app/services/pricing/plans.py

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class PricingPlan:
    name: str
    accounts: int
    min_interval_minutes: int
    daily_messages_per_account: int


PLANS: Dict[str, PricingPlan] = {
    "solo": PricingPlan(
        name="solo",
        accounts=1,
        min_interval_minutes=30,
        daily_messages_per_account=40,
    ),
    "starter": PricingPlan(
        name="starter",
        accounts=2,
        min_interval_minutes=15,
        daily_messages_per_account=80,
    ),
    "growth": PricingPlan(
        name="growth",
        accounts=5,
        min_interval_minutes=10,
        daily_messages_per_account=150,
    ),
    "pro": PricingPlan(
        name="pro",
        accounts=10,
        min_interval_minutes=5,
        daily_messages_per_account=300,
    ),
}


def get_plan(plan_name: str) -> PricingPlan:
    try:
        return PLANS[plan_name]
    except KeyError:
        raise ValueError(f"Unknown pricing plan: {plan_name}")
