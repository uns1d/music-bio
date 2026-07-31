import os
import sys

import pytest


@pytest.fixture(scope="session")
def qt_application():
    if sys.platform != "win32":
        yield None
        return

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_QUICK_BACKEND", "software")

    from PySide6.QtWidgets import QApplication

    application = QApplication.instance() or QApplication([])
    yield application
    application.processEvents()
