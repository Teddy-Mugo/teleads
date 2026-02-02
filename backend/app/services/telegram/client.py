import asyncio
from pathlib import Path
from typing import Optional

from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    SessionPasswordNeededError,
    RPCError,
)
# stringsession import
from loguru import logger


class TelegramClientWrapper:
    """
    Wrapper around Telethon TelegramClient for user accounts.
    One instance = one Telegram account.
    """

    def __init__(
        self,
        *,
        session_name: str,
        api_id: int,
        api_hash: str,
        session_dir: str = "sessions",
        proxy: Optional[dict] = None,
    ):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = session_name
        self.proxy = proxy

        self.session_path = Path(session_dir)
        self.session_path.mkdir(parents=True, exist_ok=True)

        self.client: Optional[TelegramClient] = None

    def _build_client(self) -> TelegramClient:
        session_file = self.session_path / self.session_name

        logger.info(f"Initializing Telegram client [{self.session_name}]")

        return TelegramClient(
            session=str(session_file),
            api_id=self.api_id,
            api_hash=self.api_hash,
            proxy=self.proxy,
            device_model="Desktop",
            system_version="Windows 10",
            app_version="1.0",
            lang_code="en",
        )

    async def connect(self) -> TelegramClient:
        if self.client is None:
            self.client = self._build_client()

        if not self.client.is_connected():
            await self.client.connect()

        if not await self.client.is_user_authorized():
            logger.warning(f"Account [{self.session_name}] is NOT authorized")
            raise RuntimeError("Telegram account not authorized")

        logger.success(f"Connected Telegram client [{self.session_name}]")
        return self.client

    async def disconnect(self):
        if self.client and self.client.is_connected():
            await self.client.disconnect()
            logger.info(f"Disconnected Telegram client [{self.session_name}]") 

            #we intentionally use connect() not start() here to avoid re-authorization

    async def ensure_connection(self) -> TelegramClient:
        """
        Safe helper that always returns a connected client.
        """
        try:
            return await self.connect()
        except FloodWaitError as e:
            logger.error(
                f"FloodWait ({e.seconds}s) on connect for [{self.session_name}]"
            )
            raise
        except RPCError as e:
            logger.exception(f"RPC error on connect [{self.session_name}]")
            raise

    async def __aenter__(self) -> TelegramClient:
        return await self.ensure_connection()

    async def __aexit__(self, exc_type, exc, tb):
        await self.disconnect()



