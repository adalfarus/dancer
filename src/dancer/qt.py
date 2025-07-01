"""Qt-Specific GUI addons to dancer"""
from PySide6 import QtCore as _QtCore, QtGui as _QtGui, QtWidgets as _QtWidgets
from PySide6.QtWidgets import (QMessageBox as _QMessageBox, QCheckBox as _QCheckBox, QBoxLayout as _QBoxLayout,
                               QWidget as _QWidget, QLayout as _QLayout, QApplication as _QApplication)
from PySide6.QtCore import Qt as _Qt, QTimer as _QTimer, QObject as _QObject, Signal as _Signal
from argparse import Namespace as _Ns
import sys

from . import DefaultAppGUI as _DefaultGUIApp

__all__ = ["QQuickMessageBox", "QBoxDirection", "QNoSpacingBoxLayout", "QtTimidTimer", "DefaultAppGUIQt"]

MBoxIcon = _QMessageBox.Icon
MBoxButton = _QMessageBox.StandardButton

class QQuickMessageBox(_QMessageBox):
    """TBA"""
    def __init__(self, parent=None, icon: MBoxIcon | None = None, window_title: str = "", text: str = "",
                 detailed_text: str = "", checkbox: _QCheckBox | None = None,
                 standard_buttons: MBoxButton | None = MBoxButton.Ok,
                 default_button: MBoxButton | None = None):
        """
        An advanced QMessageBox with additional configuration options.

        :param parent: The parent widget.
        :param icon: The icon to display.
        :param window_title: The title of the message box window.
        :param text: The text to display.
        :param detailed_text: The detailed text to display.
        :param checkbox: A QCheckBox instance.
        :param standard_buttons: The standard buttons to include.
        :param default_button: The default button.
        """
        super().__init__(parent)
        for arg, func in zip([standard_buttons, icon, window_title, text, detailed_text, checkbox, default_button],
                             ["setStandardButtons", "setIcon", "setWindowTitle", "setText", "setDetailedText",
                              "setCheckBox", "setDefaultButton"]):
            if arg:
                getattr(self, func)(arg)

        # Set the window to stay on top initially
        self.setWindowState(self.windowState() & ~_Qt.WindowState.WindowMaximized)

        self.raise_()
        self.activateWindow()


QBoxDirection = _QBoxLayout.Direction


class QQuickBoxLayout(_QBoxLayout):
    """TBA"""
    def __init__(self, direction: _QBoxLayout.Direction, spacing: int = 9,
                 margins: tuple[int, int, int, int] = (9, 9, 9, 9), *contents: _QLayout | _QWidget,
                 apply_layout_to: _QWidget | None = None, parent: _QWidget | None = None):
        super().__init__(direction, parent)
        self.setContentsMargins(*margins)
        self.setSpacing(spacing)

        for content in contents:
            if isinstance(content, _QLayout):
                self.addLayout(content)
            elif isinstance(content, _QWidget):
                self.addWidget(content)

        if apply_layout_to is not None:
            apply_layout_to.setLayout(self)


class QNoSpacingBoxLayout(QQuickBoxLayout):
    """TBA"""
    def __init__(self, direction: _QBoxLayout.Direction, *contents: _QLayout | _QWidget,
                 apply_layout_to: _QWidget | None = None, parent: _QWidget | None = None):
        super().__init__(direction, 0, (0, 0, 0, 0), *contents,
                         apply_layout_to=apply_layout_to, parent=parent)


class QtTimidTimer(_QObject):
    """
    A Qt-based version of TimidTimer using QTimer for seamless integration with the Qt event loop.
    """
    timeout = _Signal(int)  # Signal emitted on timeout, with index of timer.

    def __init__(self, parent: _QWidget | None = None) -> None:
        super().__init__(parent)
        self._timers: dict[int, _QTimer | None] = {}  # dict of active timers

    def start(self, interval_ms: int, index: int | None = None):
        """
        Start a timer with the given interval.

        Args:
            interval_ms (int): Timer interval in milliseconds.
            index (int): Optional index to identify the timer.
        """
        timer = _QTimer(self)
        timer.setInterval(interval_ms)
        timer.setSingleShot(False)
        timer.timeout.connect(lambda: self._on_timeout(index if index is not None else len(self._timers)))
        self._timers[index] = timer
        timer.start()

    def stop(self, index: int):
        """
        Stop a timer by its index.

        Args:
            index (int): The index of the timer to stop.
        """
        if index in self._timers:
            self._timers[index].stop()
            self._timers[index].deleteLater()
            self._timers[index] = None
        else:
            raise Exception("Invalid index")

    def _on_timeout(self, index: int):
        """
        Internal method called when a timer times out.

        Args:
            index (int): The index of the timer that timed out.
        """
        self.timeout.emit(index)  # Emit signal with the timer index.

    def stop_all(self):
        """
        Stop all active timers.
        """
        for timer in self._timers.values():
            if timer is not None:
                timer.stop()
                timer.deleteLater()
        self._timers.clear()

    def is_active(self, index: int) -> bool:
        """
        Check if a specific timer is active.

        Args:
            index (int): The index of the timer.

        Returns:
            bool: True if the timer is active, False otherwise.
        """
        return index in self._timers and self._timers[index] is not None and self._timers[index].isActive()


class QtAppSettings(_QObject):
    _instance: _ty.Self | None = None
    _initialized: bool = False
    setup: bool = False

    # Settings Signals
    test_setting_changed = _Signal(str)

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppSettings, cls).__new__(cls)
            # cls._instance._initialized = False  # Track initialization state
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:  # Prevent reinitialization
            return
        super().__init__()
        self._initialized = True

    def init(self) -> None:
        """Initializes the AppSettings"""
        if self.setup:  # Prevent reinitialization
            return
        # Do some stuff ...
        self.setup = True

    def _retrieve(self, name: str) -> _ty.Any:
        raise NotImplementedError()
    def _store(self, name: str, value: _ty.Any) -> None:
        raise NotImplementedError()

    # Settings Methods
    def get_test_setting(self) -> str:
        return self._retrieve("test_setting")
    def set_test_setting(self, test_setting: str) -> None:
        self._store("test_setting", test_setting)
        self.test_setting_changed.emit(test_setting)

# TODO: Add theme stuff to qt app
class DefaultAppGUIQt(_DefaultGUIApp):
    def __init__(self, window, logs_directory: str, parsed_args: _Ns, logging_level: int, /, setup_thread_pool: bool = False) -> None:
        super().__init__(logs_directory, parsed_args, logging_level, setup_thread_pool=setup_thread_pool)

        self.window = window

        # Setup window
        self.system: BaseSystemType = get_system()
        self.os_theme: SystemTheme = self.get_os_theme()
        self.current_theming: str = ""
        self.load_themes(os.path.join(self.styling_folder, "themes"))
        self.load_styles(os.path.join(self.styling_folder, "styles"))

        self.window.setup_gui(self.ui_automaton)

        x, y, width, height = self.settings.get_window_geometry()
        if not self.settings.get_save_window_dimensions():
            width = 1050
            height = 640
        if self.settings.get_save_window_position():
            self.window.set_window_geometry(x, y + 31, width, height)  # Somehow saves it as 31 pixels less,
        else:  # I guess windows does some weird shit with the title bar
            self.window.set_window_dimensions(width, height)

        assign_object_names_iterative(self.window.internal_obj())  # Set object names for theming
        self.apply_theme()

        self.window.start()  # Shows gui
        self.update_font()  # So that everything gets updated

        self.timer_number: int = 1
        self.timer: QtTimidTimer = QtTimidTimer()
        self.timer.timeout.connect(self.timer_tick)
        self.timer.start(500, 0)

    def open_url(self, url: str) -> None:
        QDesktopServices.openUrl(QUrl(url))

    def button_popup(self, title: str, text: str, description: str,
                     icon: _ty.Literal["Information", "Critical", "Question", "Warning", "NoIcon"],
                     buttons: list[str], default_button: str, checkbox: str | None = None) -> tuple[str | None, bool]:
        if checkbox is not None:
            checkbox = QCheckBox(checkbox)
        msg_box = QQuickMessageBox(self, getattr(QMessageBox.Icon, icon), title, text,
                                   checkbox=checkbox, standard_buttons=None, default_button=None)
        button_map: dict[str, QPushButton] = {}
        for button_str in buttons:
            button = QPushButton(button_str)
            button_map[button_str] = button
            msg_box.addButton(button, QMessageBox.ButtonRole.ActionRole)
        custom_button = button_map.get(default_button)
        if custom_button is not None:
            msg_box.setDefaultButton(custom_button)
        msg_box.setDetailedText(description)

        clicked_button: int = msg_box.exec()

        checkbox_checked = False
        if checkbox is not None:
            checkbox_checked = checkbox.isChecked()

        for button_text, button_obj in button_map.items():
            if msg_box.clickedButton() == button_obj:
                return button_text, checkbox_checked
        return None, checkbox_checked

    def load_themes(self, theme_folder: str, clear: bool = False) -> None:
        """Loads all theme files from styling/themes"""
        if clear:
            Theme.clear_loaded_themes()
        for file in os.listdir(theme_folder):
            if file.endswith(".th"):
                path = os.path.join(theme_folder, file)
                Theme.load_from_file(path)

        if Theme.get_loaded_theme("adalfarus::base") is None:
            raise RuntimeError(f"Base theme is not present")

    def load_styles(self, style_folder: str, clear: bool = False) -> None:
        """Loads all styles from styling/styles"""
        if clear:
            Style.clear_loaded_styles()
        for file in os.listdir(style_folder):
            if file.endswith(".st"):
                path = os.path.join(style_folder, file)
                Style.load_from_file(path)

        if (Style.get_loaded_style("Default Dark", "*") is None
                or Style.get_loaded_style("Default Light", "*") is None):
            raise RuntimeError(f"Default light and/or dark style are/is not present")

    def apply_theme(self) -> None:
        theming_str: str = self.settings.get_theming(self.os_theme)
        self.current_theming = theming_str
        theme_str, style_str = theming_str.split("/", maxsplit=1)
        theme: Theme | None = Theme.get_loaded_theme(theme_str)

        if theme is None:  # TODO: Popup
            IOManager().warning(f"Specified theme '{theme}' is not available", "", show_dialog=True)
            return
        style: Style | None = theme.get_compatible_style(style_str.replace("_", " ").title())
        if style is None:
            IOManager().warning(f"Couldn't find specified style {style_str} for theme {theme_str}", "",
                                show_dialog=True)
            return
        theme_str, palette = theme.apply_style(style, QPalette(),
                                               transparency_mode="none")  # TODO: Get from settings
        self.qapp.setPalette(palette)
        self.window.set_global_theme(theme_str, getattr(self.window.AppStyle, theme.get_base_styling()))

    def check_theme_change(self):
        if self.timer_number & 1 == 1:
            current_os_theme = self.get_os_theme()
            if current_os_theme != self.os_theme or self.settings.get_theming(current_os_theme) != self.current_theming:
                self.os_theme = current_os_theme
                self.apply_theme()

    def timer_tick(self, index: int) -> None:
        if index == 0:  # Default 500ms timer
            super().timer_tick()
            self.check_theme_change()
            self.timer_number += 1
            if self.timer_number > 999:
                self.timer_number = 1

    def exec(self) -> int:
        self.qapp = _QtWidgets.QApplication(sys.argv)
        self.window.show()
        return self.qapp.exec()

    def crash(self, error_title: str, error_text: str, error_description: str) -> bool:
        icon: _QtGui.QIcon
        if error_title == "Warning":
            icon = _QtGui.QIcon(_QtWidgets.QMessageBox.standardIcon(_QtWidgets.QMessageBox.Icon.Warning))
        else:
            icon = _QtGui.QIcon(_QtWidgets.QMessageBox.standardIcon(_QtWidgets.QMessageBox.Icon.Critical))
        custom_icon: bool = False
        if hasattr(self, "abs_window_icon_path"):
            icon_path: str = self.abs_window_icon_path
            icon = _QtGui.QIcon(icon_path)
            custom_icon = True
        msg_box = QQuickMessageBox(None, _QtWidgets.QMessageBox.Icon.Warning if custom_icon else None, error_title, error_text,
                                   error_description,
                                   standard_buttons=_QtWidgets.QMessageBox.StandardButton.Ok | _QtWidgets.QMessageBox.StandardButton.Retry,
                                   default_button=_QtWidgets.QMessageBox.StandardButton.Ok)
        msg_box.setWindowIcon(icon)
        pressed_button = msg_box.exec()
        if pressed_button == _QtWidgets.QMessageBox.StandardButton.Retry:
            return True
        return False

    def close(self) -> None:
        """Cleans up resources"""
        if hasattr(self, "timer"):
            self.timer.stop_all()
        if hasattr(self, "pool"):
            self.pool.shutdown()
        if hasattr(self, "qapp"):
            if self.qapp is not None:
                instance = qapp.instance()
                if instance is not None:
                    instance.quit()
