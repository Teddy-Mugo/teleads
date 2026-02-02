from datetime import datetime, timedelta
from typing import Optional

import redis
from loguru import logger


class AccountHealthStatus:
    HEALTHY = "healthy"
    WARNING = "warning"
    PAUSED = "paused"
    BANNED = "banned"


class AccountHealthReport:
    def __init__(
        self,
        status: str,
        reason: Optional[str] = None,
        retry_after: Optional[int] = None,
    ):
        self.status = status
        self.reason = reason
        self.retry_after = retry_after


class AccountHealthMonitor:
    """
    Tracks Telegram account health using Redis signals.
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        *,
        flood_threshold: int = 3,
        flood_window_minutes: int = 60,
        pause_minutes: int = 120,
    ):
        self.redis = redis_client
        self.flood_threshold = flood_threshold
        self.flood_window_minutes = flood_window_minutes
        self.pause_minutes = pause_minutes

    # --------------------
    # Redis keys
    # --------------------

    def _flood_key(self, account_id: str) -> str:
        return f"acct:{account_id}:flood"

    def _pause_key(self, account_id: str) -> str:
        return f"acct:{account_id}:paused_until"

    def _ban_key(self, account_id: str) -> str:
        return f"acct:{account_id}:banned"

    # --------------------
    # Recording events
    # --------------------

    def record_floodwait(self, account_id: str, seconds: int):
        """
        Record a FloodWait event.
        """
        key = self._flood_key(account_id)

        pipe = self.redis.pipeline()
        pipe.incr(key, 1)
        pipe.expire(key, self.flood_window_minutes * 60)
        pipe.execute()

        logger.warning(
            f"FloodWait recorded for [{account_id}] ({seconds}s)"
        )

        if self.redis.get(key) and int(self.redis.get(key)) >= self.flood_threshold:
            self._pause_account(account_id)

    def record_write_forbidden(self, account_id: str):
        """
        Group ban or write restriction.
        """
        logger.warning(f"Write forbidden for [{account_id}]")

    def record_ban(self, account_id: str):
        """
        Account appears banned or deactivated.
        """
        self.redis.set(self._ban_key(account_id), "1")
        logger.critical(f"Account [{account_id}] marked as BANNED")

    # --------------------
    # State transitions
    # --------------------

    def _pause_account(self, account_id: str):
        paused_until = datetime.utcnow() + timedelta(minutes=self.pause_minutes)
        self.redis.set(
            self._pause_key(account_id),
            paused_until.isoformat(),
        )

        logger.warning(
            f"Account [{account_id}] paused until {paused_until}"
        )

    # --------------------
    # Health checks
    # --------------------

    def check_health(self, account_id: str) -> AccountHealthReport:
        """
        Returns current health status for account.
        """
        if self.redis.exists(self._ban_key(account_id)):
            return AccountHealthReport(
                status=AccountHealthStatus.BANNED,
                reason="ACCOUNT_BANNED",
            )

        paused_until = self.redis.get(self._pause_key(account_id))
        if paused_until:
            paused_until_dt = datetime.fromisoformat(paused_until.decode())
            if datetime.utcnow() < paused_until_dt:
                retry_after = int(
                    (paused_until_dt - datetime.utcnow()).total_seconds()
                )
                return AccountHealthReport(
                    status=AccountHealthStatus.PAUSED,
                    reason="TEMPORARY_PAUSE",
                    retry_after=retry_after,
                )
            else:
                self.redis.delete(self._pause_key(account_id))

        flood_count = self.redis.get(self._flood_key(account_id))
        if flood_count and int(flood_count) > 0:
            return AccountHealthReport(
                status=AccountHealthStatus.WARNING,
                reason="RECENT_FLOODWAIT",
            )

        return AccountHealthReport(status=AccountHealthStatus.HEALTHY)
