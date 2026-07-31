import sys
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows Qt controller test")

if sys.platform == "win32":
    from music_bio.gui.controller import AppController
    from music_bio.storage import MemorySecretBackend, SettingsStore


def connection_values():
    return {
        "api_id": 12345,
        "phone": "+79990000000",
        "api_hash": "api-hash",
        "yandex_token": "yandex-token",
        "source_mode": "browser",
        "proxy_enabled": False,
        "proxy_host": "",
        "proxy_port": 443,
        "proxy_secret": "",
        "bridge_port": 8767,
        "bridge_token": "bridge-token",
    }


def test_saving_connections_restarts_running_engine(tmp_path, qt_application):
    assert qt_application is not None
    controller = AppController(SettingsStore(tmp_path, MemorySecretBackend()))
    runtime = MagicMock()
    runtime.running = True
    controller._runtime = runtime

    assert controller.saveConnections(connection_values())

    assert controller._restart_pending
    runtime.stop.assert_called_once_with()
    assert controller._restart_timer.isActive()

    controller._cancel_pending_restart()


def test_saving_connections_does_not_start_stopped_engine(tmp_path, qt_application):
    assert qt_application is not None
    controller = AppController(SettingsStore(tmp_path, MemorySecretBackend()))
    runtime = MagicMock()
    runtime.running = False
    controller._runtime = runtime

    assert controller.saveConnections(connection_values())

    assert not controller._restart_pending
    runtime.stop.assert_not_called()
    assert not controller._restart_timer.isActive()
