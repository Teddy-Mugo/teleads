import asyncio
import random
from datetime import datetime, timezone, date

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from telethon.errors import FloodWaitError, RPCError
from loguru import logger

from app.core.db import SessionLocal
from app.models.models import TelegramAccount, TelegramAccountDailyUsage
from app.services.telegram.client import TelegramClientWrapper


TEST_TARGET = "https://t.me/+HLMxQ5dw-qQ0MTJk"
TEST_MESSAGE = "🚀 Adbot worker loop test message"

MIN_DELAY = 45
MAX_DELAY = 90


class DailyCounter:
    def __init__(self):
        self.date = date.today()
        self.count = 0

    def reset_if_needed(self):
        if self.date != date.today():
            self.date = date.today()
            self.count = 0



# Helper function to get or create daily usage record

def get_or_create_daily_usage(db: Session, account: TelegramAccount):
    today = date.today()

    usage = (
        db.query(TelegramAccountDailyUsage)
        .filter(
            TelegramAccountDailyUsage.telegram_account_id == account.id,
            TelegramAccountDailyUsage.usage_date == today,
        )
        .first()
    )

    if usage:
        return usage

    usage = TelegramAccountDailyUsage(
        telegram_account_id=account.id,
        usage_date=today,
        messages_sent=0,
    )

    db.add(usage)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # race condition safety
        usage = (
            db.query(TelegramAccountDailyUsage)
            .filter(
                TelegramAccountDailyUsage.telegram_account_id == account.id,
                TelegramAccountDailyUsage.usage_date == today,
            )
            .first()
        )

    return usage

# The main worker loop

async def worker_loop(account: TelegramAccount):
    wrapper = TelegramClientWrapper(
        session_name=account.session_name,
        api_id=account.api_id,
        api_hash=account.api_hash,
    )

    db = SessionLocal()
    daily_limit = account.daily_message_limit or 40



    async with wrapper as client:
        logger.success(f"Worker started for {account.phone_number}")

        while True:
            usage = get_or_create_daily_usage(db, account)

            if usage.messages_sent >= daily_limit:
                logger.info(
                    f"Daily limit reached for {account.phone_number}, sleeping 1h"
                )
                await asyncio.sleep(3600)
                continue

            try:
                await client.send_message(
                    TEST_TARGET,
                    TEST_MESSAGE,
                )
                
                usage.messages_sent += 1
                db.commit()

                logger.info(
                    f"Sent message for {account.phone_number}"
                )

                account.last_used_at = datetime.now(timezone.utc)

                delay = random.randint(MIN_DELAY, MAX_DELAY)
                logger.info(f"Sleeping {delay}s")
                await asyncio.sleep(delay)

            except FloodWaitError as e:
                logger.warning(
                    f"FloodWait {e.seconds}s for {account.phone_number}"
                )
                await asyncio.sleep(e.seconds + 10)

            except RPCError:
                logger.exception(
                    f"Telegram RPC error for {account.phone_number}"
                )
                await asyncio.sleep(300)


async def main():
    db: Session = SessionLocal()

    try:
        account = (
            db.query(TelegramAccount)
            .filter(TelegramAccount.status == "active")
            .first()
        )

        if not account:
            logger.error("No active telegram accounts found")
            return

        await worker_loop(account)
        db.commit()

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())

    
