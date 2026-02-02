import asyncio
import random
import datetime

from telethon import functions, types
from telethon.errors import FloodWaitError

from app.core.db import SessionLocal
from app.models.models import TelegramAccount, AccountHealthEvent
from app.services.client import get_client_for_account


async def perform_warmup_action(client, action):
    dialogs = await client.get_dialogs(limit=10)
    if not dialogs:
        return

    dialog = random.choice(dialogs)

    if action == "read":
        await client.send_read_acknowledge(dialog)

    elif action == "react":
        msg = await client.get_messages(dialog, limit=1)
        if msg:
            await client(functions.messages.SendReactionRequest(
                peer=dialog.entity,
                msg_id=msg[0].id,
                reaction=[types.ReactionEmoji(emoticon="👍")],
            ))

    elif action == "send":
        await client.send_message(dialog, "Nice 👍")

    elif action == "join":
        # Example public group — replace with SAFE list
        await client(functions.channels.JoinChannelRequest(
            channel="https://t.me/telegram"
        ))



async def warmup_account(account: TelegramAccount):
    db = SessionLocal()

    try:
        client = await get_client_for_account(account)

        actions = WARMUP_PLAN.get(account.warmup_day, ["read"])

        daily_actions = random.randint(1, len(actions) + 1)

        for _ in range(daily_actions):
            action = random.choice(actions)

            try:
                await perform_warmup_action(client, action)
                await asyncio.sleep(random.randint(30, 120))

            except FloodWaitError as e:
                account.status = "paused"
                db.add(AccountHealthEvent(
                    account_id=account.id,
                    event_type="floodwait",
                    details=f"Warmup floodwait {e.seconds}s",
                ))
                db.commit()
                return

        # Advance warm-up
        if account.warmup_day >= 5:
            account.status = "active"
            account.warmup_completed = True
        else:
            account.warmup_day += 1

        db.commit()

    finally:
        db.close()



async def warmup_loop():
    while True:
        db = SessionLocal()

        try:
            accounts = (
                db.query(TelegramAccount)
                .filter(
                    TelegramAccount.status == "warming",
                    TelegramAccount.warmup_completed == False,
                )
                .all()
            )

            for account in accounts:
                await warmup_account(account)
                await asyncio.sleep(random.randint(300, 900))  # long pause

        finally:
            db.close()

        await asyncio.sleep(3600)  # run hourly
