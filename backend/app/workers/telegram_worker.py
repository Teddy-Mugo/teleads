import asyncio
import random
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy.orm import Session
from telethon.errors import FloodWaitError, RPCError

from app.core.db import SessionLocal
from app.models.models import (
    Campaign,
    TelegramAccount,
    TelegramGroup,
    MessageLog,
    MarketList,
    CampaignGroup,
)
from app.services.telegram.client import TelegramClientWrapper
from app.services.campaigns.message_variator import MessageVariator
from app.services.pricing.enforcement import (
    validate_campaign_against_plan,
)
from app.workers.warmup import apply_warmup
from app.services.pricing.plans import get_plan
from app.services.rate_limit.account_limiter import (
    can_send_message,
    record_message_sent,
)
from app.services.rate_limit.campaign_limiter import (
    campaign_interval_passed,
    record_campaign_send,
)


MIN_DELAY = 45
MAX_DELAY = 120


# --------------------------------------------------
# Single-account send
# --------------------------------------------------

async def send_with_account(
    *,
    account: TelegramAccount,
    campaign: Campaign,
    group: TelegramGroup,
    db: Session,
):
    wrapper = TelegramClientWrapper(
        session_name=account.session_name,
        api_id=account.api_id,
        api_hash=account.api_hash,
    )

    variator = MessageVariator()

    async with wrapper as client:
        try:
            final_message = variator.vary(campaign.message)

            await client.send_message(
                entity=group.username or group.invite_link,
                message=final_message,
            )

            account.last_used_at = datetime.now(timezone.utc)

            log = MessageLog(
                campaign_id=campaign.id,
                telegram_account_id=account.id,
                telegram_group_id=group.id,
                sent_at=datetime.now(timezone.utc),
            )

            db.add(log)
            db.commit()

            logger.success(
                f"[{account.phone_number}] → {group.title}"
            )

        except FloodWaitError as e:
            logger.warning(
                f"[{account.phone_number}] FloodWait {e.seconds}s"
            )
            await asyncio.sleep(e.seconds + 10)

        except RPCError:
            logger.exception(
                f"[{account.phone_number}] Telegram RPC error"
            )

        except Exception:
            logger.exception(
                f"[{account.phone_number}] Unexpected error"
            )


# --------------------------------------------------
# Campaign execution (single safe tick)
# --------------------------------------------------

async def run_campaign_once(campaign_id):
    db: Session = SessionLocal()

    try:
        campaign = (
            db.query(Campaign)
            .filter(Campaign.id == campaign_id)
            .first()
        )

        if not campaign:
            logger.error("Campaign not found")
            return

        customer = campaign.customer

        # --------------------------------------------------
        # Pricing enforcement (interval only)
        # --------------------------------------------------
        validate_campaign_against_plan(
            campaign=campaign,
            plan_name=customer.subscription_tier,
        )

        plan = get_plan(customer.subscription_tier)

        # --------------------------------------------------
        # Campaign interval check (REDIS)
        # --------------------------------------------------
        if not campaign_interval_passed(
            campaign_id=str(campaign.id),
            interval_minutes=campaign.interval_minutes,
        ):
            logger.debug(
                f"Campaign {campaign.id} still in cooldown"
            )
            return

        # --------------------------------------------------
        # Load dedicated Telegram accounts
        # --------------------------------------------------
        accounts = (
            db.query(TelegramAccount)
            .filter(
                TelegramAccount.owner_customer_id == customer.id,
                TelegramAccount.status.in_(["warming", "active"]),
            )
            .order_by(
                TelegramAccount.last_used_at.asc().nullsfirst()
            )
            .limit(plan.accounts)
            .all()
        )

        if not accounts:
            logger.warning("No usable Telegram accounts")
            return

        # --------------------------------------------------
        # Load campaign groups (markets)
        # --------------------------------------------------
        groups = (
            db.query(TelegramGroup)
            .join(CampaignGroup)
            .filter(CampaignGroup.campaign_id == campaign.id)
            .all()
        )

        if not groups:
            logger.warning("Campaign has no target groups")
            return

        random.shuffle(groups)

        # --------------------------------------------------
        # Dispatch sends (SEQUENTIAL PER TICK — SAFE)
        # --------------------------------------------------
        for account in accounts:
            # DAILY ACCOUNT LIMIT (REDIS)
            if not can_send_message(
                account_id=str(account.id),
                daily_limit=plan.daily_messages_per_account,
            ):
                logger.info(
                    f"Account {account.phone_number} exhausted for today"
                )
                continue

            group = groups.pop(0) if groups else None
            if not group:
                break

            apply_warmup(account)
            db.commit()

            try:
                await send_with_account(
                    account=account,
                    campaign=campaign,
                    group=group,
                    db=db,
                )

                # --------------------------------------
                # RECORD SUCCESS (REDIS)
                # --------------------------------------
                record_message_sent(
                    account_id=str(account.id)
                )
                record_campaign_send(
                    str(campaign.id)
                )

                account.last_used_at = datetime.now(timezone.utc)
                db.commit()

                logger.success(
                    f"Campaign {campaign.id} → "
                    f"{group.username} via {account.phone_number}"
                )

            except Exception:
                logger.exception(
                    f"Send failed for account {account.phone_number}"
                )

            # Randomized delay between sends
            await asyncio.sleep(
                random.randint(MIN_DELAY, MAX_DELAY)
            )

    finally:
        db.close()
