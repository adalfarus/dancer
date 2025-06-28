"""Dancer"""
from . import config
from argparse import ArgumentParser as _Ag, Namespace as _Ns
from traceback import format_exc
import logging
import sys
import os

from collections import abc as _a
import typing as _ty


class Frontend:
    """Different frontends"""
    TUI = 0
    QT = 1
    TKINTER = 2

class MainClass(_ty.Protocol):
    """The main class that gets executed."""
    def __init__(self, parsed_args: _Ns, logging_mode: int) -> None: ...
    def exec(self) -> int: ...
    def close(self) -> None: ...

def start(frontend: Frontend, main_class: _ty.Type[MainClass], arg_parser: _Ag | None = None, EXIT_CODES: dict[int, _a.Callable[[], None]] | None = None) -> None:
    """Starts the app and handles error catching"""
    if EXIT_CODES is None:
        EXIT_CODES = {
        1000: lambda: os.execv(sys.executable, [sys.executable] + sys.argv[1:])  # RESTART_CODE (only works compiled)
    }
    if arg_parser is None:
        arg_parser = _Ag(description=f"{config.PROGRAM_NAME}")
    print(f"Starting {config.PROGRAM_NAME} {str(config.VERSION) + config.VERSION_ADD} with py{'.'.join([str(x) for x in sys.version_info])} ...")
    if frontend == Frontend.QT:
        from aplustools.io.qtquick import QQuickMessageBox
        from PySide6.QtWidgets import QApplication, QMessageBox
        from PySide6.QtGui import QIcon
        qapp: QApplication | None = None
    dp_app: MainClass | None = None
    current_exit_code: int = -1

    arg_parser.add_argument("--logging-mode", choices=["DEBUG", "INFO", "WARN", "WARNING", "ERROR"], default=None,
                        help="Logging mode (default: None)")
    args = arg_parser.parse_args()

    logging_mode: str = args.logging_mode
    logging_level: int | None = None
    if logging_mode is not None:
        logging_level = getattr(logging, logging_mode.upper(), None)
        if logging_level is None:
            logging.error(f"Invalid logging mode: {logging_mode}")
            logging_level = 0

    try:
        if frontend == Frontend.TUI:
            dp_app = main_class(args, logging_level)
            current_exit_code = dp_app.exec()
        elif frontend == Frontend.QT:
            qapp = QApplication(sys.argv)
            dp_app = main_class(args, logging_level)  # Shows gui
            dp_app.qapp = qapp  # Sets qapp attribute
            current_exit_code = qapp.exec()
        elif frontend == Frontend.TKINTER:
            raise NotImplementedError("Tkinter frontend is currently unsupported")
    except Exception as e:
        perm_error = False
        if isinstance(e.__cause__, PermissionError):
            perm_error = True
        if frontend == Frontend.QT:
            icon: QIcon
        if perm_error:
            error_title = "Warning"
            if frontend == Frontend.QT:
                icon = QIcon(QMessageBox.standardIcon(QMessageBox.Icon.Warning))
            error_text = (f"{config.PROGRAM_NAME} encountered a permission error. This error is unrecoverable.     \n"
                          "Make sure no other instance is running and that no internal app files are open.     ")
        else:
            error_title = "Fatal Error"
            if frontend == Frontend.QT:
                icon = QIcon(QMessageBox.standardIcon(QMessageBox.Icon.Critical))
            error_text = (f"There was an error while running the app {config.PROGRAM_NAME}.\n"
                          "This error is unrecoverable.\n"
                          "Please submit the details to our GitHub issues page.")
        error_description = format_exc()

        if frontend == Frontend.TUI:
            print(f"--- {error_title} ---\n{error_text} Do you want to restart the app?")
            inp: str = input("[Y]/n\n> ")
            if inp.upper() == "Y":
                current_exit_code = 1000
        elif frontend == Frontend.QT:
            custom_icon: bool = False
            if dp_app is not None and hasattr(dp_app, "abs_window_icon_path"):
                icon_path = dp_app.abs_window_icon_path
                icon = QIcon(icon_path)
                custom_icon = True

            msg_box = QQuickMessageBox(None, QMessageBox.Icon.Warning if custom_icon else None, error_title, error_text,
                                       error_description,
                                       standard_buttons=QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Retry,
                                       default_button=QMessageBox.StandardButton.Ok)
            msg_box.setWindowIcon(icon)
            pressed_button = msg_box.exec()
            if pressed_button == QMessageBox.StandardButton.Retry:
                current_exit_code = 1000

        logger: logging.Logger = logging.getLogger("ActLogger")
        if not logger.hasHandlers():
            print(error_description.strip())  # We print, in case the logger is not initialized yet
        else:
            for line in error_description.strip().split("\n"):
                logger.error(line)
    finally:
        if dp_app is not None:
            dp_app.close()
        # if qgui is not None:
        #     qgui.close()
        if frontend == Frontend.QT and qapp is not None:
            instance = qapp.instance()
            if instance is not None:
                instance.quit()
        # results: str = diagnose_shutdown_blockers(return_result=True)
        EXIT_CODES.get(current_exit_code, lambda: sys.exit(current_exit_code))()
