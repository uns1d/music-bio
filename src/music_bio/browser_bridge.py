import asyncio
import hmac
import json
import logging
import time
from collections.abc import Callable
from dataclasses import replace
from http import HTTPStatus
from typing import Any
from urllib.parse import urlparse

from music_bio.models import MediaTrack

logger = logging.getLogger(__name__)

_ALLOWED_HOSTS = {"music.yandex.ru", "music.yandex.com"}
_ALLOWED_ORIGINS = {
    "https://music.yandex.ru",
    "https://music.yandex.com",
}
_MAX_HEADER_BYTES = 16_384
_MAX_BODY_BYTES = 65_536


class BrowserBridgeSource:
    def __init__(
        self,
        port: int = 8765,
        token: str = "",
        stale_after: float = 6.0,
        status_callback: Callable[[bool, str], None] | None = None,
    ) -> None:
        self._port = port
        self._token = token
        self._stale_after = stale_after
        self._server: asyncio.Server | None = None
        self._track: MediaTrack | None = None
        self._last_message_at = 0.0
        self._track_updated_at = 0.0
        self._track_page_id = ""
        self._connected = False
        self._status_callback = status_callback

    async def start(self) -> None:
        if self._server is not None:
            return
        if not self._token:
            raise RuntimeError("Не задан токен браузерного моста.")
        try:
            self._server = await asyncio.start_server(
                self._handle_client,
                host="127.0.0.1",
                port=self._port,
            )
        except OSError as error:
            message = f"Не удалось открыть локальный порт {self._port}: {error}"
            self._emit_status(False, message)
            raise RuntimeError(message) from error
        logger.info("Браузерный мост запущен на 127.0.0.1:%d.", self._port)
        self._emit_status(False, "Ожидание расширения Яндекс Музыки")

    async def stop(self) -> None:
        server = self._server
        self._server = None
        self._track = None
        self._track_page_id = ""
        self._emit_status(False, "Браузерный мост остановлен")
        if server is None:
            return
        server.close()
        await server.wait_closed()

    async def get_active_track(self) -> MediaTrack | None:
        now = time.monotonic()
        if self._connected and now - self._last_message_at > self._stale_after:
            self._track = None
            self._track_page_id = ""
            self._emit_status(False, "Расширение Яндекс Музыки не отвечает")
            return None

        track = self._track
        if track is None:
            return None

        elapsed = now - self._track_updated_at
        if elapsed > self._stale_after:
            self._track = None
            self._track_page_id = ""
            return None

        position = track.position
        if track.playback_status == "PLAYING":
            position += elapsed
        if track.duration > 0:
            position = min(position, track.duration)
        return replace(track, position=position)

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        try:
            request = await asyncio.wait_for(
                self._read_request(reader),
                timeout=3.0,
            )
            status, payload, origin = self._process_request(request)
        except (TimeoutError, ValueError, json.JSONDecodeError) as error:
            status = HTTPStatus.BAD_REQUEST
            payload = {"ok": False, "error": str(error)}
            origin = ""
        except Exception:
            logger.exception("Ошибка браузерного моста.")
            status = HTTPStatus.INTERNAL_SERVER_ERROR
            payload = {"ok": False, "error": "internal_error"}
            origin = ""

        self._write_response(writer, status, payload, origin)
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    async def _read_request(self, reader: asyncio.StreamReader) -> dict[str, Any]:
        raw_headers = await reader.readuntil(b"\r\n\r\n")
        if len(raw_headers) > _MAX_HEADER_BYTES:
            raise ValueError("headers_too_large")

        lines = raw_headers.decode("latin-1").split("\r\n")
        method, path, _ = lines[0].split(" ", 2)
        headers: dict[str, str] = {}
        for line in lines[1:]:
            if not line:
                continue
            name, value = line.split(":", 1)
            headers[name.casefold()] = value.strip()

        length = int(headers.get("content-length", "0"))
        if length > _MAX_BODY_BYTES:
            raise ValueError("body_too_large")
        body = await reader.readexactly(length) if length else b""
        return {
            "method": method.upper(),
            "path": path,
            "headers": headers,
            "body": body,
        }

    def _process_request(
        self,
        request: dict[str, Any],
    ) -> tuple[HTTPStatus, dict[str, Any], str]:
        method = request["method"]
        path = request["path"]
        headers = request["headers"]
        origin = headers.get("origin", "")

        if method == "OPTIONS":
            return HTTPStatus.OK, {"ok": True}, origin
        if origin and not self._origin_allowed(origin):
            return HTTPStatus.FORBIDDEN, {"ok": False, "error": "invalid_origin"}, origin
        received_token = headers.get("authorization", "")
        if not hmac.compare_digest(received_token, f"Bearer {self._token}"):
            return HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "unauthorized"}, origin
        if path == "/v1/ping" and method == "GET":
            self._last_message_at = time.monotonic()
            self._emit_status(True, "Браузерное расширение подключено")
            return HTTPStatus.OK, {"ok": True}, origin
        if path != "/v1/track" or method != "POST":
            return HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"}, origin

        data = json.loads(request["body"].decode("utf-8"))
        source_url = str(data.get("url", ""))
        if not self._is_yandex_music_url(source_url):
            return HTTPStatus.FORBIDDEN, {"ok": False, "error": "invalid_source"}, origin

        now = time.monotonic()
        previous_updated_at = self._track_updated_at
        previous_track = self._track
        page_id = str(data.get("page_id", "")).strip()[:128]
        same_page = not page_id or not self._track_page_id or page_id == self._track_page_id
        self._last_message_at = now
        self._emit_status(True, "Браузерное расширение подключено")

        title = str(data.get("title", "")).strip()
        artist = str(data.get("artist", "")).strip()
        if data.get("active") is False or not title:
            if same_page:
                self._track = None
                self._track_page_id = ""
            return HTTPStatus.OK, {"ok": True}, origin

        playing = bool(data.get("playing"))
        if (
            previous_track is not None
            and not same_page
            and previous_track.playback_status == "PLAYING"
            and not playing
            and now - previous_updated_at <= self._stale_after
        ):
            return HTTPStatus.OK, {"ok": True}, origin

        position = self._as_non_negative_float(data.get("position"))
        duration = self._as_non_negative_float(data.get("duration"))
        position_known = bool(
            data.get(
                "position_known",
                position > 0 or duration > 0,
            )
        )
        same_track = previous_track is not None and previous_track.key == (
            artist.casefold(),
            title.casefold(),
        )
        if same_track and not position_known:
            position = previous_track.position
            if previous_track.playback_status == "PLAYING":
                elapsed = max(0.0, now - previous_updated_at)
                position += elapsed
            duration = previous_track.duration
        elif same_track and duration <= 0:
            duration = previous_track.duration

        if duration > 0:
            position = min(position, duration)

        self._track = MediaTrack(
            title=title,
            artist=artist,
            position=position,
            duration=duration,
            artwork_url=(
                str(data.get("artwork_url", "")).strip()
                or (previous_track.artwork_url if same_track else "")
            ),
            app_id="music.yandex.ru",
            playback_status="PLAYING" if playing else "PAUSED",
            source_name="Яндекс Музыка в браузере",
        )
        self._track_updated_at = now
        self._track_page_id = page_id
        return HTTPStatus.OK, {"ok": True}, origin

    def _emit_status(self, connected: bool, message: str) -> None:
        if self._connected == connected and connected:
            return
        self._connected = connected
        if self._status_callback is None:
            return
        try:
            self._status_callback(connected, message)
        except Exception:
            logger.exception("Обработчик состояния браузерного моста завершился ошибкой.")

    @staticmethod
    def _is_yandex_music_url(value: str) -> bool:
        parsed = urlparse(value)
        return parsed.scheme == "https" and parsed.hostname in _ALLOWED_HOSTS

    @staticmethod
    def _as_non_negative_float(value: Any) -> float:
        try:
            return max(0.0, float(value))
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _write_response(
        writer: asyncio.StreamWriter,
        status: HTTPStatus,
        payload: dict[str, Any],
        origin: str,
    ) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        allowed_origin = origin if BrowserBridgeSource._origin_allowed(origin) else "null"
        headers = [
            f"HTTP/1.1 {status.value} {status.phrase}",
            "Content-Type: application/json; charset=utf-8",
            f"Content-Length: {len(body)}",
            "Connection: close",
            f"Access-Control-Allow-Origin: {allowed_origin}",
            "Access-Control-Allow-Methods: GET, POST, OPTIONS",
            "Access-Control-Allow-Headers: Authorization, Content-Type",
            "Access-Control-Allow-Private-Network: true",
            "Vary: Origin",
            "",
            "",
        ]
        writer.write("\r\n".join(headers).encode("latin-1") + body)

    @staticmethod
    def _origin_allowed(origin: str) -> bool:
        return (
            origin in _ALLOWED_ORIGINS
            or origin.startswith("chrome-extension://")
            or origin.startswith("extension://")
        )
