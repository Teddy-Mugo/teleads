import asyncio
import random
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy.orm import Session
from telethon.errors import FloodWaitError, RPCError

from app.core.db import SessionLocal
from app.models.models import TelegramAccount, DailyCounter
from app.services.telegram.client import TelegramClientWrapper
from app.workers.warmup import apply_warmup
from app.services.campaigns.executor import get_next_campaign_target
from app.services.campaigns.message_variator import MessageVariator
from app.services.campaigns.rate_limiter import RateLimiter
from app.core.redis import redis_client


# -------------------------
# Timing (human-like)
# -------------------------
MIN_DELAY = 60      # 1 min
MAX_DELAY = 180     # 3 min


async def worker_loop(account: TelegramAccount, db: Session):
    logger.info(f"Starting worker for {account.phone_number}")

    wrapper = TelegramClientWrapper(
        session_name=account.session_name,
        api_id=account.api_id,
        api_hash=account.api_hash,
    )

    variator = MessageVariator()
    limiter = RateLimiter(
        redis_client,
        account_daily_limit=account.daily_message_limit,
    )

    async with wrapper as client:
        while True:
            try:
                # -------------------------
                # DAILY COUNTER (DB)
                # -------------------------
                counter = (
                    db.query(DailyCounter)
                    .filter(DailyCounter.account_id == account.id)
                    .first()
                )

                if not counter:
                    counter = DailyCounter(account_id=account.id)
                    db.add(counter)
                    db.commit()
                    db.refresh(counter)

                counter.reset_if_needed()
                db.commit()

                # -------------------------
                # APPLY WARMUP
                # -------------------------
                apply_warmup(account)
                db.commit()

                # -------------------------
                # ACCOUNT DAILY LIMIT
                # -------------------------
                rl = limiter.check_account_limit(str(account.id))
                if not rl.allowed:
                    logger.info(
                        f"[{account.phone_number}] "
                        f"Daily limit reached, sleeping {rl.retry_after}s"
                    )
                    await asyncio.sleep(rl.retry_after)
                    continue

                # -------------------------
                # GET NEXT CAMPAIGN TARGET
                # -------------------------
                target = get_next_campaign_target(db, account)
                if not target:
                    logger.debug("No eligible campaign target, sleeping 60s")
                    await asyncio.sleep(60)
                    continue

                campaign = target["campaign"]
                group = target["group"]
                raw_message = target["message"]

                # -------------------------
                # GROUP COOLDOWN
                # -------------------------
                rl = limiter.check_group_cooldown(
                    str(account.id),
                    str(group.id),
                )
                if not rl.allowed:
                    await asyncio.sleep(min(rl.retry_after, 300))
                    continue

                # -------------------------
                # SEND MESSAGE
                # -------------------------
                final_message = variator.vary(raw_message)

                await client.send_message(
                    group.telegram_id,
                    final_message,
                )

                limiter.increment_account(str(account.id))
                limiter.mark_group_posted(
                    str(account.id),
                    str(group.id),
                )

                counter.count += 1
                account.last_used_at = datetime.now(timezone.utc)

                db.commit()

                logger.success(
                    f"[{account.phone_number}] "
                    f"Sent to {group.name} ({counter.count}/{account.daily_message_limit})"
                )

                delay = random.randint(MIN_DELAY, MAX_DELAY)
                await asyncio.sleep(delay)

            except FloodWaitError as e:
                logger.warning(
                    f"[{account.phone_number}] FloodWait {e.seconds}s"
                )
                await asyncio.sleep(e.seconds + 15)

            except RPCError:
                logger.exception(
                    f"[{account.phone_number}] Telegram RPC error"
                )
                await asyncio.sleep(300)

            except Exception:
                logger.exception(
                    f"[{account.phone_number}] Worker crash recovered"
                )
                await asyncio.sleep(300)


async def main():
    db: Session = SessionLocal()

    try:
        account = (
            db.query(TelegramAccount)
            .filter(TelegramAccount.status.in_(["warming", "active"]))
            .order_by(TelegramAccount.created_at.asc())
            .first()
        )

        if not account:
            logger.error("No usable telegram accounts found")
            return

        await worker_loop(account, db)

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
