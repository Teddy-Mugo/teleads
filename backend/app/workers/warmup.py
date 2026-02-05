from datetime import datetime, timezone, timedelta
import random

from app.models.models import TelegramAccount


def apply_warmup(account: TelegramAccount) -> None:
    now = datetime.now(timezone.utc)

    if account.warmup_started_at is None:
        account.warmup_started_at = now
        account.warmup_day = 1

    days_elapsed = (now - account.warmup_started_at).days + 1
    account.warmup_day = min(days_elapsed, 5)

    if account.warmup_day <= 4:
        low, high = {
            1: (5, 8),
            2: (10, 15),
            3: (20, 25),
            4: (30, 35),
        }[account.warmup_day]

        account.daily_message_limit = random.randint(low, high)
        account.status = "warming"

    else:
        account.daily_message_limit = 45
        account.status = "active"
