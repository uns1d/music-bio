import asyncio
import logging
import threading
from collections.abc import Callable

from music_bio.app import MusicBioApplication
from music_bio.models import AppEvent, Settings
from music_bio.telegram_bio import TelegramAuthHandler, TelegramBioUpdater

logger = logging.getLogger(__name__)

EventHandler = Callable[[AppEvent], None]
AuthRequestHandler = Callable[[str, str], None]


class GuiAuthHandler(TelegramAuthHandler):
    def __init__(self, callback: AuthRequestHandler) -> None:
        self._callback = callback
        self._future: asyncio.Future[str] | None = None
        self._kind = ""

    async def request_code(self, phone: str) -> str:
        return await self._request("code", f"Код отправлен на {phone}")

    async def request_password(self) -> str:
        return await self._request("password", "Введите пароль двухэтапной защиты")

    async def _request(self, kind: str, message: str) -> str:
        loop = asyncio.get_running_loop()
        self._kind = kind
        self._future = loop.create_future()
        self._callback(kind, message)
        try:
            return await self._future
        finally:
            self._future = None
            self._kind = ""

    def submit(self, kind: str, value: str) -> None:
        future = self._future
        if future is None or future.done() or kind != self._kind:
            return
        future.set_result(value)

    def cancel(self) -> None:
        future = self._future
        if future is not None and not future.done():
            future.cancel()


class EngineRuntime:
    def __init__(
        self,
        event_handler: EventHandler,
        auth_request_handler: AuthRequestHandler,
    ) -> None:
        self._event_handler = event_handler
        self._auth_request_handler = auth_request_handler
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._application: MusicBioApplication | None = None
        self._auth_handler: GuiAuthHandler | None = None
        self._lock = threading.Lock()
        self._stop_requested = False

    @property
    def running(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive()

    def start(self, settings: Settings) -> bool:
        with self._lock:
            if self.running:
                return False
            self._stop_requested = False
            self._thread = threading.Thread(
                target=self._thread_main,
                args=(settings,),
                name="music-bio-engine",
                daemon=False,
            )
            self._thread.start()
        return True

    def stop(self) -> None:
        with self._lock:
            self._stop_requested = True
            loop = self._loop
            application = self._application
            auth_handler = self._auth_handler

        if loop is None or loop.is_closed():
            return
        if application is not None:
            loop.call_soon_threadsafe(application.request_stop)
        if auth_handler is not None:
            loop.call_soon_threadsafe(auth_handler.cancel)

    def submit_auth(self, kind: str, value: str) -> None:
        with self._lock:
            loop = self._loop
            auth_handler = self._auth_handler
        if loop is None or loop.is_closed() or auth_handler is None:
            return
        loop.call_soon_threadsafe(auth_handler.submit, kind, value)

    def shutdown(self, timeout: float = 75.0) -> None:
        self.stop()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=timeout)
            if thread.is_alive():
                logger.error(
                    "Завершение Music Bio не уложилось в %.0f сек.",
                    timeout,
                )

    def _thread_main(self, settings: Settings) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        auth_handler = GuiAuthHandler(self._auth_request_handler)
        updater = TelegramBioUpdater(
            settings,
            auth_handler=auth_handler,
            event_callback=self._event_handler,
        )
        application = MusicBioApplication(
            settings,
            bio_updater=updater,
            event_callback=self._event_handler,
        )

        with self._lock:
            self._loop = loop
            self._auth_handler = auth_handler
            self._application = application
            stop_requested = self._stop_requested
        if stop_requested:
            application.request_stop()

        try:
            loop.run_until_complete(application.run())
        except asyncio.CancelledError:
            pass
        except Exception as error:
            logger.exception("Движок Music Bio завершился с ошибкой.")
            self._event_handler(AppEvent(kind="fatal_error", message=str(error)))
        finally:
            auth_handler.cancel()
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.close()
            with self._lock:
                self._loop = None
                self._auth_handler = None
                self._application = None
