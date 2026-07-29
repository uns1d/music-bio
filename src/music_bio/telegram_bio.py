import asyncio
import logging
import os
import time

from telethon import TelegramClient, connection
from telethon.errors import FloodWaitError
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.users import GetFullUserRequest

from music_bio.models import Settings

logger = logging.getLogger(__name__)


def format_bio(
    template: str,
    artist: str,
    title: str,
    lyric: str,
    limit: int = 70,
) -> str:
    formatted = template.format(
        artist=artist,
        title=title,
        lyric=lyric,
    ).strip()

    if not lyric:
        formatted = formatted.rstrip(" |").rstrip(" -").rstrip(" —").strip()

    if not artist and "{artist}" in template:
        formatted = formatted.replace(" — ", " ").strip()

    while "  " in formatted:
        formatted = formatted.replace("  ", " ")

    if len(formatted) <= limit:
        return formatted

    return formatted[: limit - 1].rstrip() + "…"


def get_mtproxy() -> tuple[str, int, str] | None:
    host = os.environ.get("TELEGRAM_PROXY_HOST", "").strip()
    port_value = os.environ.get("TELEGRAM_PROXY_PORT", "").strip()
    secret = os.environ.get("TELEGRAM_PROXY_SECRET", "").strip()

    if not host and not port_value and not secret:
        return None

    if not host or not port_value or not secret:
        raise ValueError(
            "Для MTProxy необходимо указать TELEGRAM_PROXY_HOST, "
            "TELEGRAM_PROXY_PORT и TELEGRAM_PROXY_SECRET."
        )

    try:
        port = int(port_value)
    except ValueError as error:
        raise ValueError("TELEGRAM_PROXY_PORT должен быть целым числом.") from error

    if not 1 <= port <= 65535:
        raise ValueError("TELEGRAM_PROXY_PORT должен находиться в диапазоне 1–65535.")

    return host, port, secret


class TelegramBioUpdater:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: TelegramClient | None = None
        self._original_bio: str | None = None
        self._last_successful_bio: str | None = None
        self._bio_changed_by_script = False
        self._last_update_time: float = 0.0
        self._bio_limit: int = 70

    @property
    def original_bio(self) -> str | None:
        return self._original_bio

    @property
    def bio_limit(self) -> int:
        return self._bio_limit

    async def start(self) -> None:
        if self._settings.dry_run:
            logger.info("[DRY-RUN] Telegram-клиент не запускается.")
            return

        mtproxy = get_mtproxy()
        if mtproxy is None:
            self._client = TelegramClient(
                "music_session",
                self._settings.api_id,
                self._settings.api_hash,
            )
        else:
            host, port, secret = mtproxy
            logger.info("Подключение к Telegram через MTProxy %s:%d.", host, port)
            self._client = TelegramClient(
                "music_session",
                self._settings.api_id,
                self._settings.api_hash,
                connection=connection.ConnectionTcpMTProxyRandomizedIntermediate,
                proxy=(host, port, secret),
            )

        await self._client.start()
        await self._fetch_original_bio()

    async def _fetch_original_bio(self) -> None:
        if self._client is None:
            return

        try:
            me = await self._client.get_me()
            full_user = await self._client(GetFullUserRequest("me"))
            self._original_bio = full_user.full_user.about or ""
            self._last_successful_bio = self._original_bio
            self._bio_limit = 140 if getattr(me, "premium", False) else 70
            logger.info("Исходное Telegram Bio сохранено.")
        except Exception:
            logger.exception("Не удалось получить исходное Telegram Bio.")
            self._original_bio = None
            self._last_successful_bio = None

    async def update_bio(self, new_bio: str, force: bool = False) -> bool:
        if new_bio == self._last_successful_bio and not force:
            return False

        if self._settings.dry_run:
            self._last_successful_bio = new_bio
            logger.info("[DRY-RUN] %s", new_bio)
            return True

        if self._original_bio is None:
            logger.warning("Обновление Bio пропущено: исходное Bio не было получено.")
            return False

        now = time.monotonic()
        if not force and (now - self._last_update_time) < self._settings.min_bio_interval:
            return False

        if await self._set_bio_with_retry(new_bio):
            self._last_update_time = now
            self._last_successful_bio = new_bio
            self._bio_changed_by_script = (
                self._original_bio is not None and new_bio != self._original_bio
            )
            logger.info("Telegram Bio обновлено: %s", new_bio)
            return True

        return False

    async def _set_bio_with_retry(self, bio_text: str) -> bool:
        if self._client is None:
            return False

        try:
            await self._client(UpdateProfileRequest(about=bio_text))
            return True
        except FloodWaitError as error:
            logger.warning("Telegram FloodWait: ожидание %d сек.", error.seconds)
            await asyncio.sleep(error.seconds + 1)
            try:
                await self._client(UpdateProfileRequest(about=bio_text))
                return True
            except Exception:
                logger.exception("Повторное обновление Bio завершилось ошибкой.")
                return False
        except Exception:
            logger.exception("Не удалось обновить Telegram Bio.")
            return False

    async def stop(self) -> None:
        client = self._client
        if client is None:
            return

        try:
            if (
                not self._settings.dry_run
                and not self._settings.no_restore
                and self._bio_changed_by_script
                and self._original_bio is not None
            ):
                logger.info("Восстановление исходного Telegram Bio...")
                if await self._set_bio_with_retry(self._original_bio):
                    self._last_successful_bio = self._original_bio
                    self._bio_changed_by_script = False
                    logger.info("Исходное Telegram Bio восстановлено.")
        finally:
            await client.disconnect()
            self._client = None
            logger.info("Telegram-клиент отключён.")
