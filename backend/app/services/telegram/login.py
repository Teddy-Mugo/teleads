from pathlib import Path
from typing import Optional

from telethon import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    FloodWaitError,
    RPCError,
)
from loguru import logger


class TelegramLoginService:
    """
    Handles Telegram user account authentication and session creation.
    """

    def __init__(
        self,
        *,
        api_id: int,
        api_hash: str,
        phone_number: str,
        session_dir: str = "sessions",
        proxy: Optional[dict] = None,
    ):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone_number = phone_number
        self.proxy = proxy

        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # One session per phone number
        self.session_path = self.session_dir / self._sanitize_phone(phone_number)

        self.client = TelegramClient(
            session=str(self.session_path),
            api_id=self.api_id,
            api_hash=self.api_hash,
            proxy=self.proxy,
        )

    @staticmethod
    def _sanitize_phone(phone: str) -> str:
        """
        Removes + and spaces for safe filename usage.
        """
        return phone.replace("+", "").replace(" ", "")

    async def send_code(self):
        """
        Sends OTP to the phone number.
        """
        try:
            await self.client.connect()
            logger.info(f"Sending OTP to {self.phone_number}")

            await self.client.send_code_request(self.phone_number)
            logger.success("OTP sent successfully")

        except PhoneNumberInvalidError:
            logger.error("Invalid phone number")
            raise

        except FloodWaitError as e:
            logger.error(f"FloodWait while sending code ({e.seconds}s)")
            raise

        except RPCError:
            logger.exception("Telegram RPC error while sending code")
            raise

    async def verify_code(self, code: str, password: Optional[str] = None):
        """
        Verifies OTP (and 2FA password if required).
        """
        try:
            logger.info("Verifying OTP code")

            await self.client.sign_in(
                phone=self.phone_number,
                code=code,
            )

            logger.success("Telegram account authorized successfully")

        except PhoneCodeInvalidError:
            logger.error("Invalid OTP code")
            raise

        except SessionPasswordNeededError:
            if not password:
                logger.warning("2FA password required but not provided")
                raise

            logger.info("2FA enabled — verifying password")
            await self.client.sign_in(password=password)
            logger.success("2FA verification successful")

        except FloodWaitError as e:
            logger.error(f"FloodWait during login ({e.seconds}s)")
            raise

        except RPCError:
            logger.exception("Telegram RPC error during verification")
            raise

        finally:
            await self.client.disconnect()

    def session_exists(self) -> bool:
        """
        Checks if a session file already exists.
        """
        return self.session_path.with_suffix(".session").exists()
