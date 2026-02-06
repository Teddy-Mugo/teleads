from datetime import datetime, timezone
from app.core.redis import redis_client


def _daily_key(account_id: str) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"acct:{account_id}:sent:{today}"


def can_send_message(
    *,
    account_id: str,
    daily_limit: int,
) -> bool:
    key = _daily_key(account_id)
    sent = redis_client.get(key)
    return sent is None or int(sent) < daily_limit


def record_message_sent(
    *,
    account_id: str,
):
    key = _daily_key(account_id)

    pipe = redis_client.pipeline()
    pipe.incr(key, 1)
    pipe.expire(key, 60 * 60 * 24)
    pipe.execute()
