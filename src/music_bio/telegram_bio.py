import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Protocol

from telethon import TelegramClient, connection
from telethon.errors import FloodWaitError, SessionPasswordNeededError
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.users import GetFullUserRequest

from music_bio.models import AppEvent, EventCallback, Settings

logger = logging.getLogger(__name__)

_BIO_REQUEST_TIMEOUT = 15.0
_RESTORE_ATTEMPTS = 3
_RESTORE_MAX_FLOOD_WAIT = 60
_monotonic = time.monotonic


class TelegramAuthHandler(Protocol):
    async def request_code(self, phone: str) -> str: ...

    async def request_password(self) -> str: ...


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


def get_mtproxy(settings: Settings | None = None) -> tuple[str, int, str] | None:
    if settings is not None and settings.proxy_enabled:
        host = settings.proxy_host.strip()
        port_value = str(settings.proxy_port)
        secret = settings.proxy_secret.strip()
    else:
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
    def __init__(
        self,
        settings: Settings,
        auth_handler: TelegramAuthHandler | None = None,
        event_callback: EventCallback | None = None,
    ) -> None:
        self._settings = settings
        self._auth_handler = auth_handler
        self._event_callback = event_callback
        self._client: TelegramClient | None = None
        self._original_bio: str | None = None
        self._last_successful_bio: str | None = None
        self._bio_changed_by_script = False
        self._last_update_time = 0.0
        self._bio_limit = 70
        self._stop_event: asyncio.Event | None = None

    @property
    def original_bio(self) -> str | None:
        return self._original_bio

    @property
    def bio_limit(self) -> int:
        return self._bio_limit

    def set_stop_event(self, event: asyncio.Event) -> None:
        self._stop_event = event

    async def start(self) -> None:
        if self._settings.dry_run:
            logger.info("[DRY-RUN] Telegram-клиент не запускается.")
            self._emit_connection(True, "Режим предварительного просмотра")
            return

        self._client = self._create_client()
        if self._auth_handler is None:
            await self._client.start(phone=self._settings.telegram_phone or None)
        else:
            await self._connect_with_gui_auth()
        await self._fetch_original_bio()

    def _create_client(self) -> TelegramClient:
        session_path = Path(self._settings.session_path)
        session_path.parent.mkdir(parents=True, exist_ok=True)
        mtproxy = get_mtproxy(self._settings)
        if mtproxy is None:
            return TelegramClient(
                str(session_path),
                self._settings.api_id,
                self._settings.api_hash,
            )

        host, port, secret = mtproxy
        logger.info("Подключение к Telegram через MTProxy %s:%d.", host, port)
        return TelegramClient(
            str(session_path),
            self._settings.api_id,
            self._settings.api_hash,
            connection=connection.ConnectionTcpMTProxyRandomizedIntermediate,
            proxy=(host, port, secret),
        )

    async def _connect_with_gui_auth(self) -> None:
        assert self._client is not None
        assert self._auth_handler is not None

        await self._client.connect()
        if await self._client.is_user_authorized():
            return

        phone = self._settings.telegram_phone.strip()
        if not phone:
            raise RuntimeError("Укажите номер телефона Telegram в настройках.")

        sent = await self._client.send_code_request(phone)
        code = await self._auth_handler.request_code(phone)
        try:
            await self._client.sign_in(
                phone=phone,
                code=code,
                phone_code_hash=sent.phone_code_hash,
            )
        except SessionPasswordNeededError:
            password = await self._auth_handler.request_password()
            await self._client.sign_in(password=password)

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
            name_parts = (
                getattr(me, "first_name", ""),
                getattr(me, "last_name", ""),
            )
            display_name = " ".join(
                part.strip() for part in name_parts if isinstance(part, str) and part.strip()
            )
            self._emit_connection(True, display_name or "Telegram подключён")
        except Exception:
            self._original_bio = None
            self._last_successful_bio = None
            self._emit_connection(False, "Не удалось прочитать профиль")
            logger.exception("Не удалось прочитать исходное Telegram Bio.")

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

        now = _monotonic()
        if not force and (now - self._last_update_time) < self._settings.min_bio_interval:
            return False
        if not await self._set_bio_with_retry(new_bio):
            return False

        self._last_update_time = now
        self._last_successful_bio = new_bio
        self._bio_changed_by_script = new_bio != self._original_bio
        logger.info("Telegram Bio обновлено: %s", new_bio)
        return True

    async def _set_bio_with_retry(
        self,
        bio_text: str,
        *,
        restoring: bool = False,
    ) -> bool:
        if self._client is None:
            return False

        attempts = _RESTORE_ATTEMPTS if restoring else 2
        for attempt in range(1, attempts + 1):
            try:
                await asyncio.wait_for(
                    self._client(UpdateProfileRequest(about=bio_text)),
                    timeout=_BIO_REQUEST_TIMEOUT,
                )
                return True
            except FloodWaitError as error:
                delay = error.seconds + 1
                if restoring and delay > _RESTORE_MAX_FLOOD_WAIT:
                    logger.error(
                        "Восстановление Bio требует ожидания %d сек.; допустимый предел — %d сек.",
                        delay,
                        _RESTORE_MAX_FLOOD_WAIT,
                    )
                    return False
                logger.warning("Telegram FloodWait: ожидание %d сек.", delay)
            except Exception as error:
                if attempt == attempts:
                    logger.exception(
                        "Не удалось %s Telegram Bio после %d попыток.",
                        "восстановить" if restoring else "обновить",
                        attempts,
                    )
                    return False
                delay = min(2 ** (attempt - 1), 4)
                logger.warning(
                    "Ошибка Telegram при %s Bio: %s. Повтор через %d сек.",
                    "восстановлении" if restoring else "обновлении",
                    error,
                    delay,
                )

            if restoring:
                await asyncio.sleep(delay)
            elif await self._wait_or_stop(delay):
                return False

        return False

    async def _wait_or_stop(self, delay: float) -> bool:
        stop_event = self._stop_event
        if stop_event is None:
            await asyncio.sleep(delay)
            return False
        if stop_event.is_set():
            return True

        sleep_task = asyncio.create_task(asyncio.sleep(delay))
        stop_task = asyncio.create_task(stop_event.wait())
        tasks = (sleep_task, stop_task)
        try:
            done, _ = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED,
            )
            return stop_task in done and stop_event.is_set()
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

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
                if await self._set_bio_with_retry(
                    self._original_bio,
                    restoring=True,
                ):
                    self._last_successful_bio = self._original_bio
                    self._bio_changed_by_script = False
                    logger.info("Исходное Telegram Bio восстановлено.")
                else:
                    logger.error(
                        "Исходное Telegram Bio не восстановлено. "
                        "Проверьте соединение и повторите запуск с остановкой."
                    )
        finally:
            await client.disconnect()
            self._client = None
            self._emit_connection(False, "Telegram отключён")
            logger.info("Telegram-клиент отключён.")

    def _emit_connection(self, connected: bool, message: str) -> None:
        if self._event_callback is None:
            return
        self._event_callback(
            AppEvent(
                kind="connection",
                service="telegram",
                connected=connected,
                message=message,
            )
        )
