import asyncio
from app.services.telegram.client import get_client

async def main():
    client = get_client("+254728629439")
    await client.start()

    await client.send_message("me", "♻️ Reused session works")
    print("Message sent")

    await client.disconnect()

asyncio.run(main())
