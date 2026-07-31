import logging
import signal
import sys
from collections.abc import Callable
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QAction, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from music_bio.gui.controller import AppController
from music_bio.storage import default_app_dir


def main() -> int:
    _configure_logging()
    QQuickStyle.setStyle("Basic")

    application = QApplication(sys.argv)
    application.setApplicationName("Music Bio")
    application.setOrganizationName("uns1d")
    application.setQuitOnLastWindowClosed(False)

    package_dir = Path(__file__).resolve().parent
    icon_path = package_dir / "gui" / "resources" / "music-bio.svg"
    qml_path = package_dir / "gui" / "qml" / "Main.qml"
    icon = QIcon(str(icon_path))
    application.setWindowIcon(icon)

    controller = AppController()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", controller)
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        return 1

    window = engine.rootObjects()[0]
    tray, request_quit = _create_tray(application, controller, window, icon)
    tray.show()
    signal_timer = QTimer(application)
    signal_timer.setInterval(250)
    signal_timer.timeout.connect(lambda: None)
    signal_timer.start()

    def handle_exit_signal(*_args: object) -> None:
        QTimer.singleShot(0, request_quit)

    signal.signal(signal.SIGINT, handle_exit_signal)
    signal.signal(signal.SIGTERM, handle_exit_signal)

    def show_window(*_args: object) -> None:
        window.show()
        window.raise_()
        window.requestActivate()

    controller.authRequested.connect(show_window)
    controller.deviceAuthReady.connect(show_window)
    application.aboutToQuit.connect(controller.shutdown)
    try:
        return application.exec()
    finally:
        controller.shutdown()


def _create_tray(
    application: QApplication,
    controller: AppController,
    window: object,
    icon: QIcon,
) -> tuple[QSystemTrayIcon, Callable[[], None]]:
    tray = QSystemTrayIcon(icon, application)
    tray.setToolTip("Music Bio")
    menu = QMenu()
    quitting = False
    quit_timer = QTimer(application)
    quit_timer.setInterval(100)

    show_action = QAction("Открыть Music Bio", menu)

    def show_window(*_args: object) -> None:
        window.show()
        window.raise_()
        window.requestActivate()

    show_action.triggered.connect(show_window)
    menu.addAction(show_action)

    start_action = QAction("Запустить", menu)

    def start_engine() -> None:
        show_window()
        controller.startEngine()

    start_action.triggered.connect(start_engine)
    menu.addAction(start_action)

    stop_action = QAction("Остановить", menu)
    stop_action.triggered.connect(controller.stopEngine)
    menu.addAction(stop_action)

    overlay_action = QAction("Показать или скрыть оверлей", menu)
    overlay_action.triggered.connect(controller.toggleOverlay)
    menu.addAction(overlay_action)
    menu.addSeparator()

    quit_action = QAction("Выйти", menu)

    def finish_quit() -> None:
        if controller.engine_running:
            return
        quit_timer.stop()
        tray.hide()
        window.setProperty("closingForReal", True)
        application.quit()

    def quit_application() -> None:
        nonlocal quitting
        if quitting:
            return
        quitting = True
        quit_action.setEnabled(False)
        tray.setToolTip("Music Bio — восстановление исходного Bio")
        tray.showMessage(
            "Music Bio",
            "Восстанавливаю исходное Telegram Bio перед выходом…",
        )
        controller.stopEngine()
        finish_quit()
        if controller.engine_running:
            quit_timer.start()

    quit_action.triggered.connect(quit_application)
    quit_timer.timeout.connect(finish_quit)
    menu.addAction(quit_action)
    tray.setContextMenu(menu)

    def activate(reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if window.isVisible():
                window.hide()
            else:
                window.show()
                window.raise_()
                window.requestActivate()

    tray.activated.connect(activate)
    return tray, quit_application


def _configure_logging() -> None:
    log_dir = default_app_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = RotatingFileHandler(
        log_dir / "music-bio.log",
        maxBytes=1_500_000,
        backupCount=2,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, stream_handler],
    )


if __name__ == "__main__":
    raise SystemExit(main())
