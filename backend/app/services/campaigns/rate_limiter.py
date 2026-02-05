from datetime import datetime, timedelta
from typing import Optional

import redis
from loguru import logger


class RateLimitResult:
    def __init__(
        self,
        allowed: bool,
        reason: Optional[str] = None,
        retry_after: Optional[int] = None,
    ):
        self.allowed = allowed
        self.reason = reason
        self.retry_after = retry_after


class RateLimiter:
    """
    Redis-backed rate limiter for Telegram accounts and groups.

    Guarantees:
    - Per-account daily limits
    - Per-group cooldowns
    - Auto-reset at UTC midnight
    - Stateless worker safety
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        *,
        account_daily_limit: int = 40,
        group_cooldown_minutes: int = 1440,  # 24h default
    ):
        self.redis = redis_client
        self.account_daily_limit = account_daily_limit
        self.group_cooldown_minutes = group_cooldown_minutes

    # --------------------------------------------------
    # Redis key helpers
    # --------------------------------------------------

    def _account_day_key(self, account_id: str) -> str:
        date = datetime.utcnow().strftime("%Y-%m-%d")
        return f"acct:{account_id}:count:{date}"

    def _group_last_post_key(self, account_id: str, group_id: str) -> str:
        return f"acct:{account_id}:group:{group_id}:last_post"

    # --------------------------------------------------
    # Account-level daily limit
    # --------------------------------------------------

    def check_account_limit(self, account_id: str) -> RateLimitResult:
        key = self._account_day_key(account_id)
        count = self.redis.get(key)

        if count is not None and int(count) >= self.account_daily_limit:
            logger.warning(
                f"Account [{account_id}] daily limit reached"
            )
            return RateLimitResult(
                allowed=False,
                reason="ACCOUNT_DAILY_LIMIT",
                retry_after=self._seconds_until_midnight(),
            )

        return RateLimitResult(allowed=True)

    def increment_account(self, account_id: str):
        """
        Increments daily counter and ensures it expires at midnight UTC.
        """
        key = self._account_day_key(account_id)

        pipe = self.redis.pipeline()
        pipe.incr(key, 1)
        pipe.expireat(key, self._midnight_timestamp())
        pipe.execute()

    # --------------------------------------------------
    # Group-level cooldown
    # --------------------------------------------------

    def check_group_cooldown(
        self,
        account_id: str,
        group_id: str,
    ) -> RateLimitResult:
        key = self._group_last_post_key(account_id, group_id)
        last_post = self.redis.get(key)

        if last_post:
            last_post_time = datetime.fromisoformat(
                last_post.decode()
            )
            next_allowed = last_post_time + timedelta(
                minutes=self.group_cooldown_minutes
            )

            if datetime.utcnow() < next_allowed:
                retry_after = int(
                    (next_allowed - datetime.utcnow()).total_seconds()
                )
                logger.warning(
                    f"Group cooldown active "
                    f"[group={group_id}] [account={account_id}]"
                )
                return RateLimitResult(
                    allowed=False,
                    reason="GROUP_COOLDOWN",
                    retry_after=retry_after,
                )

        return RateLimitResult(allowed=True)

    def mark_group_posted(self, account_id: str, group_id: str):
        """
        Marks a group as posted to and automatically clears after cooldown.
        """
        key = self._group_last_post_key(account_id, group_id)

        self.redis.set(
            key,
            datetime.utcnow().isoformat(),
            ex=self.group_cooldown_minutes * 60,
        )

    # --------------------------------------------------
    # Unified check (RECOMMENDED ENTRY POINT)
    # --------------------------------------------------

    def check_all(
        self,
        account_id: str,
        group_id: str,
    ) -> RateLimitResult:
        """
        Checks account + group limits in the correct order.
        """
        acct = self.check_account_limit(account_id)
        if not acct.allowed:
            return acct

        grp = self.check_group_cooldown(account_id, group_id)
        if not grp.allowed:
            return grp

        return RateLimitResult(allowed=True)

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    @staticmethod
    def _midnight_timestamp() -> int:
        tomorrow = datetime.utcnow().date() + timedelta(days=1)
        return int(
            datetime.combine(
                tomorrow,
                datetime.min.time(),
            ).timestamp()
        )

    @staticmethod
    def _seconds_until_midnight() -> int:
        midnight = datetime.combine(
            datetime.utcnow().date() + timedelta(days=1),
            datetime.min.time(),
        )
        return int(
            (midnight - datetime.utcnow()).total_seconds()
        )
