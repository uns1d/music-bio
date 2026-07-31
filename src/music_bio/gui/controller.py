import hashlib
import socket
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QGuiApplication
from yandex_music import Client

from music_bio.gui.runtime import EngineRuntime
from music_bio.models import AppEvent, ApplicationState, Settings, SourceMode
from music_bio.storage import SettingsStore, parse_mtproxy_url

_PALETTES = [
    ("#7666D5", "#4CB6A7", "#A7658A"),
    ("#B97752", "#A89355", "#A9555D"),
    ("#4E9B78", "#4B9AA0", "#5877AE"),
    ("#9270B2", "#7079AE", "#4F8FA3"),
    ("#AD6371", "#7B6DA0", "#5B819F"),
]


class AppController(QObject):
    stateChanged = Signal()
    trackChanged = Signal()
    connectionsChanged = Signal()
    settingsChanged = Signal()
    overlayChanged = Signal()
    activityChanged = Signal()
    authRequested = Signal(str, str)
    deviceAuthReady = Signal(str, str)
    toastRequested = Signal(str, bool)
    _runtimeEvent = Signal(object)
    _runtimeAuthRequest = Signal(str, str)

    def __init__(self, store: SettingsStore | None = None) -> None:
        super().__init__()
        self._store = store or SettingsStore()
        self._runtime = EngineRuntime(
            event_handler=self._runtimeEvent.emit,
            auth_request_handler=self._runtimeAuthRequest.emit,
        )
        self._state = ApplicationState.STOPPED.value
        self._status_message = "Готов к запуску"
        self._artist = ""
        self._title = ""
        self._lyric = ""
        self._next_lyric = ""
        self._bio = ""
        self._cover_url = ""
        self._position = 0.0
        self._duration = 0.0
        self._playback_status = ""
        self._source_name = ""
        self._accent_primary = "#7666D5"
        self._accent_secondary = "#4CB6A7"
        self._accent_tertiary = "#A7658A"
        self._telegram_connected = False
        self._yandex_connected = False
        self._browser_connected = False
        self._browser_status = "Мост ещё не запускался"
        self._lyrics_connected = False
        self._proxy_connected = False
        self._overlay_visible = False
        self._activity: list[str] = []
        self._restart_pending = False
        self._restart_timer = QTimer(self)
        self._restart_timer.setInterval(75)
        self._restart_timer.timeout.connect(self._complete_pending_restart)
        self._runtimeEvent.connect(self._handle_event)
        self._runtimeAuthRequest.connect(self.authRequested.emit)
        self._append_activity("Music Bio 2.0 готов")

    @Property(str, notify=stateChanged)
    def state(self) -> str:
        return self._state

    @Property(str, notify=stateChanged)
    def statusMessage(self) -> str:
        return self._status_message

    @Property(bool, notify=stateChanged)
    def running(self) -> bool:
        return self._state in {
            ApplicationState.STARTING.value,
            ApplicationState.RUNNING.value,
            ApplicationState.STOPPING.value,
        }

    @Property(str, notify=trackChanged)
    def artist(self) -> str:
        return self._artist

    @Property(str, notify=trackChanged)
    def title(self) -> str:
        return self._title

    @Property(str, notify=trackChanged)
    def lyric(self) -> str:
        return self._lyric

    @Property(str, notify=trackChanged)
    def nextLyric(self) -> str:
        return self._next_lyric

    @Property(str, notify=trackChanged)
    def bioPreview(self) -> str:
        return self._bio

    @Property(str, notify=trackChanged)
    def coverUrl(self) -> str:
        return self._cover_url

    @Property(float, notify=trackChanged)
    def position(self) -> float:
        return self._position

    @Property(float, notify=trackChanged)
    def duration(self) -> float:
        return self._duration

    @Property(float, notify=trackChanged)
    def progress(self) -> float:
        if self._duration <= 0:
            return 0.0
        return min(1.0, max(0.0, self._position / self._duration))

    @Property(bool, notify=trackChanged)
    def playing(self) -> bool:
        return self._playback_status == "PLAYING"

    @Property(bool, notify=trackChanged)
    def paused(self) -> bool:
        return self._playback_status == "PAUSED"

    @Property(str, notify=trackChanged)
    def sourceName(self) -> str:
        return self._source_name

    @Property(str, notify=trackChanged)
    def accentPrimary(self) -> str:
        return self._accent_primary

    @Property(str, notify=trackChanged)
    def accentSecondary(self) -> str:
        return self._accent_secondary

    @Property(str, notify=trackChanged)
    def accentTertiary(self) -> str:
        return self._accent_tertiary

    @Property(bool, notify=connectionsChanged)
    def telegramConnected(self) -> bool:
        return self._telegram_connected

    @Property(bool, notify=connectionsChanged)
    def yandexConnected(self) -> bool:
        return self._yandex_connected

    @Property(bool, notify=connectionsChanged)
    def browserConnected(self) -> bool:
        return self._browser_connected

    @Property(str, notify=connectionsChanged)
    def browserStatus(self) -> str:
        return self._browser_status

    @Property(bool, notify=connectionsChanged)
    def lyricsConnected(self) -> bool:
        return self._lyrics_connected

    @Property(bool, notify=connectionsChanged)
    def proxyConnected(self) -> bool:
        return self._proxy_connected

    @Property("QVariantMap", notify=settingsChanged)
    def settings(self) -> dict[str, Any]:
        values = self._store.public_values()
        values.update(
            {
                "api_hash": self._store.secret_value("telegram_api_hash"),
                "yandex_token": self._store.secret_value("yandex_token"),
                "proxy_secret": self._store.secret_value("proxy_secret"),
                "bridge_token": self._store.ensure_bridge_token(),
            }
        )
        return values

    @Property(bool, notify=overlayChanged)
    def overlayVisible(self) -> bool:
        return self._overlay_visible

    @Property("QStringList", notify=activityChanged)
    def activity(self) -> list[str]:
        return self._activity

    @Slot()
    def startEngine(self) -> None:
        self._cancel_pending_restart()
        if self._runtime.running:
            return
        try:
            settings = self._store.runtime_settings()
            error = self._validate_settings(settings)
            if error:
                self.toastRequested.emit(error, True)
                return
            self._runtime.start(settings)
        except Exception as error:
            self.toastRequested.emit(str(error), True)

    @Slot()
    def stopEngine(self) -> None:
        self._cancel_pending_restart()
        self._runtime.stop()

    @property
    def engine_running(self) -> bool:
        return self._runtime.running

    @Slot(str, str)
    def submitAuth(self, kind: str, value: str) -> None:
        self._runtime.submit_auth(kind, value.strip())

    @Slot("QVariantMap", result=bool)
    def saveConnections(self, values: dict[str, Any]) -> bool:
        try:
            proxy_port = int(values.get("proxy_port", 443))
            bridge_port = int(values.get("bridge_port", 8765))
            if not 1 <= proxy_port <= 65535:
                raise ValueError("Порт MTProxy должен быть в диапазоне 1–65535")
            if not 1024 <= bridge_port <= 65535:
                raise ValueError("Порт браузерного моста должен быть от 1024 до 65535")
            self._store.save_connections(
                api_id=int(values.get("api_id", 0)),
                phone=str(values.get("phone", "")),
                api_hash=str(values.get("api_hash", "")),
                yandex_token=str(values.get("yandex_token", "")),
                source_mode=str(values.get("source_mode", SourceMode.BROWSER.value)),
                proxy_enabled=bool(values.get("proxy_enabled", False)),
                proxy_host=str(values.get("proxy_host", "")),
                proxy_port=proxy_port,
                proxy_secret=str(values.get("proxy_secret", "")),
                bridge_port=bridge_port,
                bridge_token=str(values.get("bridge_token", "")),
            )
        except Exception as error:
            self.toastRequested.emit(str(error), True)
            return False

        self.settingsChanged.emit()
        restarting = self._restart_after_settings_change()
        message = (
            "Настройки сохранены. Перезапускаю Music Bio…"
            if restarting
            else "Настройки подключений сохранены"
        )
        self.toastRequested.emit(message, False)
        self._append_activity("Настройки подключений обновлены")
        return True

    @Slot("QVariantMap", result=bool)
    def saveAppearance(self, values: dict[str, Any]) -> bool:
        template = str(values.get("template", "")).strip()
        try:
            preview = template.format(artist="A", title="T", lyric="L")
        except (KeyError, ValueError) as error:
            self.toastRequested.emit(f"Ошибка шаблона Bio: {error}", True)
            return False
        if not preview.strip():
            self.toastRequested.emit("Шаблон Bio не должен быть пустым", True)
            return False

        overlay_mode = str(values.get("overlay_mode", "card"))
        if overlay_mode not in {"card", "strip", "orb"}:
            self.toastRequested.emit("Неизвестный режим оверлея", True)
            return False

        self._store.update_preferences(
            lyrics_enabled=bool(values.get("lyrics_enabled", True)),
            restore_bio=bool(values.get("restore_bio", True)),
            template=template,
            check_interval=max(1.0, float(values.get("check_interval", 3.0))),
            min_bio_interval=max(
                5.0,
                float(values.get("min_bio_interval", 12.0)),
            ),
            overlay_mode=overlay_mode,
            overlay_opacity=max(
                0.45,
                min(1.0, float(values.get("overlay_opacity", 0.94))),
            ),
            overlay_always_on_top=bool(values.get("overlay_always_on_top", True)),
            overlay_click_through=bool(values.get("overlay_click_through", False)),
            animation_level=max(
                0,
                min(2, int(values.get("animation_level", 2))),
            ),
            start_minimized=bool(values.get("start_minimized", False)),
        )
        self.settingsChanged.emit()
        self.overlayChanged.emit()
        self.toastRequested.emit("Настройки оформления сохранены", False)
        return True

    @Slot(str, result="QVariantMap")
    def parseProxyLink(self, value: str) -> dict[str, Any]:
        try:
            host, port, secret = parse_mtproxy_url(value)
            return {"ok": True, "host": host, "port": port, "secret": secret}
        except ValueError as error:
            return {"ok": False, "error": str(error)}

    @Slot()
    def testProxy(self) -> None:
        preferences = self._store.preferences
        if not preferences.proxy_host or not preferences.proxy_port:
            self.toastRequested.emit("Сначала укажите сервер и порт MTProxy", True)
            return
        threading.Thread(
            target=self._test_proxy_worker,
            args=(preferences.proxy_host, preferences.proxy_port),
            daemon=True,
        ).start()

    @Slot()
    def testYandex(self) -> None:
        token = self._store.secret_value("yandex_token")
        if not token:
            self.toastRequested.emit("Сначала укажите токен Яндекс Музыки", True)
            return
        threading.Thread(
            target=self._test_yandex_worker,
            args=(token,),
            daemon=True,
        ).start()

    @Slot()
    def requestYandexToken(self) -> None:
        threading.Thread(target=self._device_auth_worker, daemon=True).start()

    @Slot()
    def toggleOverlay(self) -> None:
        self._overlay_visible = not self._overlay_visible
        self.overlayChanged.emit()

    @Slot(bool)
    def setOverlayVisible(self, visible: bool) -> None:
        self._overlay_visible = visible
        self.overlayChanged.emit()

    @Slot(str, int, int, int, int)
    def saveOverlayGeometry(
        self,
        mode: str,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
        if mode not in {"card", "strip", "orb"}:
            return
        self._store.update_preferences(
            overlay_x=x,
            overlay_y=y,
            **{
                f"overlay_{mode}_width": width,
                f"overlay_{mode}_height": height,
            },
        )

    @Slot(str)
    def copyText(self, value: str) -> None:
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(value)
        self.toastRequested.emit("Скопировано", False)

    @Slot()
    def openExtensionFolder(self) -> None:
        candidates = (
            Path(__file__).resolve().parents[3] / "browser-extension",
            Path.cwd() / "browser-extension",
        )
        extension_dir = next(
            (path for path in candidates if path.is_dir()),
            None,
        )
        if extension_dir is None:
            self.toastRequested.emit(
                "Папка browser-extension не найдена",
                True,
            )
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(extension_dir)))

    @Slot()
    def shutdown(self) -> None:
        self._cancel_pending_restart()
        self._runtime.shutdown()

    @Property(str, notify=trackChanged)
    def formattedPosition(self) -> str:
        return _format_time(self._position)

    @Property(str, notify=trackChanged)
    def formattedDuration(self) -> str:
        return _format_time(self._duration)

    def _handle_event(self, event: AppEvent) -> None:
        if event.kind == "state" and event.state is not None:
            self._state = event.state.value
            self._status_message = event.message
            self.stateChanged.emit()
            self._append_activity(event.message)
            return

        if event.kind == "fatal_error":
            self._state = ApplicationState.ERROR.value
            self._status_message = event.message
            self.stateChanged.emit()
            self.toastRequested.emit(event.message, True)
            self._append_activity(f"Ошибка: {event.message}")
            return

        if event.kind == "connection":
            if event.service == "telegram":
                self._telegram_connected = bool(event.connected)
                if self._store.preferences.proxy_enabled:
                    self._proxy_connected = bool(event.connected)
            elif event.service == "yandex":
                self._yandex_connected = bool(event.connected)
            elif event.service == "browser":
                self._browser_connected = bool(event.connected)
                self._browser_status = event.message
            elif event.service == "lyrics":
                self._lyrics_connected = bool(event.connected)
            elif event.service == "proxy":
                self._proxy_connected = bool(event.connected)
            self.connectionsChanged.emit()
            if event.message:
                self._append_activity(event.message)
            return

        if event.kind == "track":
            track = event.track
            if track is None:
                self._artist = ""
                self._title = ""
                self._lyric = ""
                self._next_lyric = ""
                self._bio = ""
                self._cover_url = ""
                self._position = 0.0
                self._duration = 0.0
                self._playback_status = ""
                self._source_name = ""
            else:
                changed = (self._artist.casefold(), self._title.casefold()) != track.key
                self._artist = track.artist
                self._title = track.title
                self._lyric = event.lyric
                self._next_lyric = event.next_lyric
                self._bio = event.bio
                self._cover_url = track.artwork_url
                self._position = track.position
                self._duration = track.duration
                self._playback_status = track.playback_status
                self._source_name = track.source_name
                if changed:
                    self._update_palette(track.artist, track.title)
                    self._append_activity(f"Новый трек: {track.artist} — {track.title}")
            self.trackChanged.emit()

    def _update_palette(self, artist: str, title: str) -> None:
        digest = hashlib.sha256(f"{artist}\0{title}".encode()).digest()
        palette = _PALETTES[digest[0] % len(_PALETTES)]
        self._accent_primary, self._accent_secondary, self._accent_tertiary = palette

    def _test_proxy_worker(self, host: str, port: int) -> None:
        try:
            with socket.create_connection((host, port), timeout=6.0):
                pass
        except OSError as error:
            self._runtimeEvent.emit(
                AppEvent(
                    kind="connection",
                    service="proxy",
                    connected=False,
                    message=f"MTProxy недоступен: {error}",
                )
            )
            self.toastRequested.emit("MTProxy недоступен", True)
            return
        self._runtimeEvent.emit(
            AppEvent(
                kind="connection",
                service="proxy",
                connected=True,
                message="MTProxy отвечает",
            )
        )
        self.toastRequested.emit("MTProxy доступен", False)

    def _test_yandex_worker(self, token: str) -> None:
        try:
            Client(token).init()
        except Exception as error:
            self._runtimeEvent.emit(
                AppEvent(
                    kind="connection",
                    service="lyrics",
                    connected=False,
                    message=f"Ошибка Яндекс Музыки: {error}",
                )
            )
            self.toastRequested.emit("Токен Яндекс Музыки не принят", True)
            return
        self._runtimeEvent.emit(
            AppEvent(
                kind="connection",
                service="lyrics",
                connected=True,
                message="Токен синхронизированных текстов работает",
            )
        )
        self.toastRequested.emit("Токен Яндекс Музыки работает", False)

    def _device_auth_worker(self) -> None:
        try:
            token = Client().device_auth(on_code=self._device_code_callback)
            self._store.set_secret("yandex_token", token.access_token)
            self.settingsChanged.emit()
            self.toastRequested.emit("Токен Яндекс Музыки сохранён", False)
        except Exception as error:
            self.toastRequested.emit(f"Не удалось получить токен: {error}", True)

    def _device_code_callback(self, code: Any) -> None:
        url = str(code.verification_url)
        user_code = str(code.user_code)
        self.deviceAuthReady.emit(url, user_code)
        webbrowser.open(url)

    def _append_activity(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M")
        self._activity = [f"{timestamp}  {message}", *self._activity[:11]]
        self.activityChanged.emit()

    def _restart_after_settings_change(self) -> bool:
        if not self._runtime.running:
            return False
        self._restart_pending = True
        self._runtime.stop()
        self._restart_timer.start()
        return True

    def _complete_pending_restart(self) -> None:
        if not self._restart_pending:
            self._restart_timer.stop()
            return
        if self._runtime.running:
            return

        self._restart_pending = False
        self._restart_timer.stop()
        self.startEngine()

    def _cancel_pending_restart(self) -> None:
        self._restart_pending = False
        self._restart_timer.stop()

    @staticmethod
    def _validate_settings(settings: Settings) -> str:
        if settings.api_id <= 0:
            return "Укажите Telegram API ID"
        if not settings.api_hash:
            return "Укажите Telegram API Hash"
        if not settings.no_lyrics and not settings.yandex_token:
            return "Укажите токен Яндекс Музыки или отключите тексты"
        if settings.source_mode in {SourceMode.BROWSER, SourceMode.AUTO}:
            if not settings.browser_bridge_token:
                return "Не задан токен браузерного моста"
            if not 1024 <= settings.browser_bridge_port <= 65535:
                return "Порт браузерного моста должен быть от 1024 до 65535"
        if settings.proxy_enabled:
            if not settings.proxy_host or not settings.proxy_secret:
                return "Заполните все поля MTProxy"
            if not 1 <= settings.proxy_port <= 65535:
                return "Порт MTProxy должен быть в диапазоне 1–65535"
        return ""


def _format_time(seconds: float) -> str:
    total = max(0, int(seconds))
    return f"{total // 60:02d}:{total % 60:02d}"
