from datetime import datetime, timezone
from app.core.redis import redis_client


def _campaign_key(campaign_id: str) -> str:
    return f"campaign:{campaign_id}:last_sent"


def campaign_interval_passed(
    *,
    campaign_id: str,
    interval_minutes: int,
) -> bool:
    last = redis_client.get(_campaign_key(campaign_id))
    if not last:
        return True

    last_dt = datetime.fromisoformat(last)
    delta = datetime.now(timezone.utc) - last_dt
    return delta.total_seconds() >= interval_minutes * 60


def record_campaign_send(campaign_id: str):
    redis_client.set(
        _campaign_key(campaign_id),
        datetime.now(timezone.utc).isoformat(),
    )
