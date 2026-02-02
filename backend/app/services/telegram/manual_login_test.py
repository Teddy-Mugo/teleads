import asyncio
from pathlib import Path
from telethon import TelegramClient
from app.services.telegram.config import API_ID, API_HASH

PHONE_NUMBER = "+254728629439"

BASE_DIR = Path(__file__).resolve().parents[3]  # backend/
SESSIONS_DIR = BASE_DIR / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)

async def main():
    client = TelegramClient(
        session=str(SESSIONS_DIR / PHONE_NUMBER),
        api_id=API_ID,
        api_hash=API_HASH,
    )

    await client.start(phone=PHONE_NUMBER)
    print("✅ Login successful")

    me = await client.get_me()
    print("Logged in as:", me.username or me.id)

    await client.disconnect()

asyncio.run(main())
