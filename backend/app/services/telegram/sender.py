import asyncio
import random
from datetime import datetime
from typing import Optional, Union

from telethon.errors import (
    FloodWaitError,
    ChatWriteForbiddenError,
    UserBannedInChannelError,
    RPCError,
)
from telethon.tl.types import InputPeerChannel, InputPeerChat

from loguru import logger

from app.services.telegram.client import TelegramClientWrapper


class TelegramSendResult:
    """
    Structured result for message send attempts.
    """

    def __init__(
        self,
        success: bool,
        error: Optional[str] = None,
        flood_wait: Optional[int] = None,
        timestamp: Optional[datetime] = None,
    ):
        self.success = success
        self.error = error
        self.flood_wait = flood_wait
        self.timestamp = timestamp or datetime.utcnow()


class TelegramSender:
    """
    Safe message sender with rate limiting & FloodWait handling.
    """

    def __init__(
        self,
        *,
        client_wrapper: TelegramClientWrapper,
        min_delay: int = 30,
        max_delay: int = 90,
    ):
        self.client_wrapper = client_wrapper
        self.min_delay = min_delay
        self.max_delay = max_delay

    async def _random_delay(self):
        delay = random.randint(self.min_delay, self.max_delay)
        logger.debug(f"Sleeping {delay}s before sending message")
        await asyncio.sleep(delay)

    async def send_message(
        self,
        *,
        entity: Union[str, int],
        message: str,
        parse_mode: Optional[str] = None,
        link_preview: bool = False,
    ) -> TelegramSendResult:
        """
        Sends a message to a group/channel/user.

        entity:
          - @username
          - group/channel ID
        """

        await self._random_delay()

        try:
            async with self.client_wrapper as client:
                logger.info(
                    f"Sending message using [{self.client_wrapper.session_name}] "
                    f"to [{entity}]"
                )

                await client.send_message(
                    entity=entity,
                    message=message,
                    parse_mode=parse_mode,
                    link_preview=link_preview,
                )

                logger.success("Message sent successfully")

                return TelegramSendResult(success=True)

        except FloodWaitError as e:
            logger.error(f"FloodWait {e.seconds}s while sending message")
            return TelegramSendResult(
                success=False,
                error="FLOOD_WAIT",
                flood_wait=e.seconds,
            )

        except (ChatWriteForbiddenError, UserBannedInChannelError):
            logger.error("Write forbidden / banned in target")
            return TelegramSendResult(
                success=False,
                error="WRITE_FORBIDDEN",
            )

        except RPCError as e:
            logger.exception("Telegram RPC error while sending message")
            return TelegramSendResult(
                success=False,
                error=str(e),
            )

        except Exception:
            logger.exception("Unexpected error while sending message")
            return TelegramSendResult(
                success=False,
                error="UNKNOWN_ERROR",
            )
