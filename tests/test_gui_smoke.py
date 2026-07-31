import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Qt smoke test")
def test_qml_application_window_loads(tmp_path, qt_application):
    from PySide6.QtCore import QUrl
    from PySide6.QtQml import QQmlApplicationEngine

    from music_bio.gui.controller import AppController
    from music_bio.storage import MemorySecretBackend, SettingsStore

    assert qt_application is not None
    controller = AppController(SettingsStore(tmp_path, MemorySecretBackend()))
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", controller)
    qml_path = (
        Path(__file__).resolve().parents[1] / "src" / "music_bio" / "gui" / "qml" / "Main.qml"
    )

    engine.load(QUrl.fromLocalFile(str(qml_path)))
    qt_application.processEvents()

    assert engine.rootObjects()
    assert engine.rootObjects()[0].property("title") == "Music Bio 2.0"

    engine.rootObjects()[0].hide()
    controller.shutdown()
