[![Active Development](https://img.shields.io/badge/Maintenance%20Level-Actively%20Developed-brightgreen.svg)](https://gist.github.com/cheerfulstoic/d107229326a01ff0f333a1d3476e068d)
[![CI Test Status](https://github.com/Adalfarus/dancer/actions/workflows/test-package.yml/badge.svg)](https://github.com/Adalfarus/dancer/actions)
[![License: LGPL-2.1](https://img.shields.io/github/license/Adalfarus/dancer)](https://github.com/Adalfarus/dancer/blob/main/LICENSE)

[//]: # (<div style="display: flex; align-items: center; width: 100%;">)

[//]: # (    <img src="project_data/dancer.png" style="height: 10vw;">)

[//]: # (    <p style="margin: 0 0 0 2vw; font-size: 10vw; color: #3b4246;">Dancer</p>)

[//]: # (</div>)
<img src="https://github.com/adalfarus/dancer/blob/main/project_data/img.png">

dancer is a simple, and user-friendly Python library for creating competent apps.

## Compatibility
🟩 (Works perfectly); 🟨 (Untested); 🟧 (Some Issues); 🟥 (Unusable)

| OS                       | UX & README instructions | Tests | More Complex Functionalities |
|--------------------------|--------------------------|-------|------------------------------|
| Windows                  | 🟩                       | 🟩    | 🟩                           |
| MacOS                    | 🟨                       | 🟩    | 🟨                           |
| Linux (Ubuntu 22.04 LTS) | 🟩                       | 🟩    | 🟩                           |

## Features

* **Makes user-specific storage easy**

  → Automatically sets up per-user directories (e.g., config, logs, plugins, styling) to isolate application data and avoid conflicts across users.

* **Comes with various data storage and encryption built-in \[IN THE FULL RELEASE]**

  → Full release will offer structured storage layers, file-based persistence, encryption helpers, and cryptographic utilities—some adapted from [`aplustools`](https://pypi.org/project/aplustools/).

* **Sets up a good environment for your app to run in**

  → Automatically constructs an organized project tree, validates Python + OS compatibility, allows for easy restarts when compiled, and supports dynamic extension loading.

* **Supports Windows, Linux and MacOS**

  → Fully cross-platform with native support for common operating systems and runtime configurations.

> ⚠️ These features are part of a larger toolkit. The examples below (GUI/TUI bootstrapping via `config` and `start`) are **only one part** of what this package enables.

## Installation

You can install `dancer` via pip:

```sh
pip install dancer --upgrade
```

If you want to use Qt-specific components:

```sh
pip install dancer[qt] --upgrade
```

This installs PySide6 which enables you to use e.g. the class DefaultQtGUIApp which has features like theme management, and more.

Or clone the repository and install manually:

```sh
git clone https://github.com/Adalfarus/dancer.git
cd dancer
python -m build
```

## Usage

Here are a few quick examples of how to use `dancer`:

### TUI Server Example

This creates a simple Flask-based TUI server. It uses `DefaultServerTUI` to manage config state, run settings, and integrate logging, but it does **not** rely on dancers Qt components. The Qt-based system tray would not make enough use of the advanced features they provide.

> This example focuses on config validation, modular settings loading, Flask integration, and minimal runtime bootstrapping.

````python
from dancer import config, start, DefaultServerTUI

from werkzeug.serving import make_server, BaseWSGIServer
from argparse import ArgumentParser, Namespace
from threading import Thread
import logging
import json
import sys
import os

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QPlainTextEdit
from PySide6.QtGui import QIcon, QAction

import typing as _ty


class QtConsoleHandler(logging.Handler):
  def __init__(self, widget: QPlainTextEdit):
    super().__init__()
    self.widget = widget

  def emit(self, record):
    msg = self.format(record)
    self.widget.appendPlainText(msg)


class App(DefaultServerTUI):
  def __init__(self, parsed_args: Namespace, logging_mode: int) -> None:
    super().__init__(os.path.abspath("./latest.log"), parsed_args, logging_mode, always_restart=True)
    from common.app import
      create_app  # This is a relative import from appdata, so we can only do it after we ran config()
    self.logger.info("Creating Flask Server ...")

    self.config_path: str = os.path.abspath("./config/core.json")
    settings_path: str = parsed_args.load_config_path or self.config_path
    self.app_settings: dict[str, _ty.Any] = self.load_settings_from_file(settings_path)
    self.app_settings.update(vars(parsed_args))
    self.write_settings_to_file(self.app_settings.copy(), self.config_path)

    self.console_window = None
    self.app = create_app(self.app_settings)
    self.ssl_context: None | tuple[str, str] = None
    self.server: BaseWSGIServer | None = None
    self.thread: Thread | None = None

    if parsed_args.run_ssl:
      if config.INDEV:
        self.ssl_context = ("./cert.pem", "./key.pem")
      else:
        self.ssl_context = (self.app_settings["certfile"], self.app_settings["keyfile"])

  @staticmethod
  def load_settings_from_file(file_path: str) -> dict[str, _ty.Any]:
    if not os.path.exists(file_path):
      return {}
    with open(file_path, "r") as f:
      return json.loads(f.read())

  @staticmethod
  def write_settings_to_file(settings: dict[str, _ty.Any], file_path: str) -> None:
    with open(file_path, "w") as f:
      f.write(json.dumps(settings, indent=4))

  def exec(self) -> int:
    self.server = make_server(host="0.0.0.0", port=3030, app=self.app, ssl_context=self.ssl_context)
    self.logger.info("Starting Flask Server ...")
    self.thread = Thread(target=self.server.serve_forever)
    self.thread.start()
    self.logger.info("Starting GUI ...")

    self.qapp = QApplication([])
    self.qapp.setQuitOnLastWindowClosed(False)

    self.console_window = QPlainTextEdit(None)
    self.handler = QtConsoleHandler(self.console_window)
    formatter = logging.Formatter(
      '[%(asctime)s.%(msecs)03d] [%(levelname)s] %(message)s',
      datefmt='%Y-%m-%d %H:%M:%S'
    )
    self.handler.setFormatter(formatter)
    self.logger.add_handler(self.handler)

    tray = QSystemTrayIcon()
    tray.setIcon(QIcon("media/icon.png"))  # This image has to exist, otherwise there won't be a tray element
    tray.setVisible(True)
    tray.setToolTip(config.PROGRAM_NAME)

    menu = QMenu()
    menu.setStyleSheet("""
            QMenu {
                color: #000000; 
                background-color: #ffffff; 
                border-radius: 5px;
            }
            QMenu::item {
                padding: 2px 10px; 
                margin: 2px 2px; 
                font-weight: bold;
            }
            QMenu::item:selected {
                background-color: #f2f2f2;
            }
        """)

    title_action = QAction(f"🔧 {config.PROGRAM_NAME} Menu")
    title_action.setEnabled(False)
    menu.addAction(title_action)
    menu.addSeparator()

    about_action = QAction("About")
    about_action.triggered.connect(self.open_about)
    menu.addAction(about_action)

    settings_action = QAction("Settings")
    settings_action.triggered.connect(self.open_settings)
    menu.addAction(settings_action)

    console_action = QAction("Console")
    console_action.triggered.connect(self.open_console)
    menu.addAction(console_action)

    restart_action = QAction("Restart")
    restart_action.triggered.connect(self.restart)
    menu.addAction(restart_action)

    quit_action = QAction("Quit")
    quit_action.triggered.connect(self.qapp.quit)
    menu.addAction(quit_action)

    for action in menu.actions():
      action.setIconVisibleInMenu(False)

    tray.setContextMenu(menu)
    self.logger.info("Entering application loop ...")
    return self.qapp.exec()

  def open_settings(self) -> None:
    pass

  def open_console(self) -> None:
    self.console_window.show()

  def open_about(self) -> None:
    pass

  def restart(self) -> None:
    self.qapp.exit(
      1000)  # Exit code 1000 is the default exit code for a restart in dancer (only works in compiled builds)

  def close(self) -> None:
    if hasattr(self, "server") and self.server is not None:
      self.server.shutdown()
    if hasattr(self, "thread") and self.thread is not None:
      self.thread.join()


if __name__ == "__main__":
  app_info = config.AppConfig(
    True, False,  # These flags are INDEV and INDEV_KEEP_RUNTIME_FILES.
    # Indev enables behavior such as replacing all appdata files.
    # They can also be checked by importing dancer.config in another file and accessing the e.g. .INDEV attribute.
    "ContentView Server",  # This is the program name
    "contentview_server",  # This is the normalized program name
    100, "a0",  # This is the version and version_add
    {"Windows": {"10": ("any",), "11": ("any",)}},  # These are the supported OS versions (major: (minor,))
    [(3, 10), (3, 11), (3, 12), (3, 13)],  # These are the supported Python versions
    {  # This is the directory structure that gets created in appdata
      "config": {},
      "core": {
        "common": {},
        "plugins": {},
        "extensions": {
          "library": {},
          "providers": {}
        }
      },
      "data": {
        "static": {},
        "templates": {}
      }
    },
    ["./"]  # These are the relative paths from default-config that are added to sys.paths
  )
  config.do(
    app_info)  # This completes the config, there is no reason to manually do it except if you want specialized behavior.

  if config.INDEV:
    os.environ["FLASK_SECRET_KEY"] = "..."
    os.environ["JWT_SECRET_KEY"] = "..."
    os.environ["PEPPER"] = "..."
    os.environ["COOKIE_SECRET_KEY"] = "..."

  parser = ArgumentParser(description=f"{config.PROGRAM_NAME}")
  parser.add_argument("library_path")
  parser.add_argument("--host", default="0.0.0.0")
  parser.add_argument("--port", type=int, default=3030)
  parser.add_argument("--static-dir", type=str, default=None)
  parser.add_argument("--templates-dir", type=str, default=None)
  parser.add_argument("--load-config-path", type=str, default=None)
  parser.add_argument("--comicview-client", type=str, default=None)
  parser.add_argument("--no-ssl", dest="run_ssl", action="store_false")
  parser.add_argument("--certfile", type=str)
  parser.add_argument("--keyfile", type=str)

  parser.add_argument("--api-only", action="store_true")
  parser.add_argument("--frontend-only", action="store_true")
  parser.add_argument("--admin-user", action="store_true")
  parser.add_argument("--rate-limit", action="store_true")

  start(App,
        parser)  # Here we pass the App class and the parser (optional) dancer will always add logging-level to the parser.
````

### Hybrid Example, a bit of TUI and a bit of GUI

You can look at this example in more detail at: https://github.com/adalfarus/unicode-writer

### GUI Example (Qt)

This shows how to structure a GUI app using `DefaultAppGUIQt`. Unlike the TUI example, this version makes full use of file-based settings, asset management, extension loading, and more. It is meant for apps with interactive UIs, not simple CLI or server tools.

You can look at this example in more detail at: https://github.com/Giesbrt/Automaten/blob/dancer-start/src/main.py

````python
from dancer import config, start
from dancer.qt import DefaultAppGUIQt

# Here we do the config setup at the top of the file
# This is done so we can access the user-specific modules in appdata as imports right after.
app_info = config.AppConfig(
  False, True,
  "N.E.F.S.' Simulator",
  "nefs_simulator",
  1400, "b4",
  {"Windows": {"10": ("any",), "11": ("any",)}},
  [(3, 10), (3, 11), (3, 12), (3, 13)],
  {
    "config": {},
    "core": {
      "libs": {},
      "modules": {}
    },
    "data": {
      "assets": {
        "app_icons": {}
      },
      "styling": {
        "styles": {},
        "themes": {}
      },
      "logs": {}
    }
  },
  ["./core/common", "./core/plugins", "./"]
)
config.do(app_info)

# Std Lib imports
from pathlib import Path as PLPath
from argparse import ArgumentParser, Namespace
from traceback import format_exc
from functools import partial
from string import Template
import multiprocessing
import threading
import logging
import sys
import os

# Third party imports
from packaging.version import Version, InvalidVersion
from returns import result as _result
import stdlib_list
import requests
# PySide6
from PySide6.QtWidgets import QApplication, QMessageBox, QSizePolicy
from PySide6.QtGui import QIcon, QDesktopServices, Qt, QPalette
from PySide6.QtCore import QUrl
# aplustools
from aplustools.io.env import diagnose_shutdown_blockers

# Internal imports (why we did config.do( ... ) early)
from automaton.UIAutomaton import UiAutomaton
from automaton.automatonProvider import AutomatonProvider
from serializer import serialize, deserialize
from storage import AppSettings
from gui import MainWindow
from abstractions import IMainWindow, IBackend, IAppSettings
from automaton import start_backend
from utils.IOManager import IOManager
from utils.staticSignal import SignalCache
from automaton.UiSettingsProvider import UiSettingsProvider
from customPythonHandler import CustomPythonHandler
from extensions_loader import Extensions_Loader
from automaton.base.QAutomatonInputWidget import QAutomatonInputOutput

# Standard typing imports for aps
import collections.abc as _a
import typing as _ty
import types as _ts

hiddenimports = list(stdlib_list.stdlib_list())
multiprocessing.freeze_support()


class App(DefaultAppGUIQt):
  def __init__(self, parsed_args: Namespace, logging_level: int) -> None:
    self.base_app_dir = config.base_app_dir
    self.data_folder = os.path.join(self.base_app_dir, "data")
    self.core_folder = os.path.join(self.base_app_dir, "core")
    self.extensions_folder = os.path.join(self.base_app_dir, "extensions")
    self.config_folder = os.path.join(self.base_app_dir, "config")
    self.styling_folder = os.path.join(self.data_folder, "styling")

    settings = AppSettings()
    settings.init(config, self.config_folder)

    super().__init__(MainWindow, settings,
                     os.path.join(self.styling_folder, "themes"),
                     os.path.join(self.styling_folder, "styles"),
                     os.path.join(self.data_folder, "logs"),
                     parsed_args, logging_level,
                     setup_thread_pool=True)

    try:
      recent_files = []
      for file in self.settings.get_recent_files():
        if os.path.exists(file):
          recent_files.append(file)
      self.settings.set_recent_files(tuple(recent_files))

      self.offload_work("load_extensions", self.set_extensions,
                        lambda: Extensions_Loader(self.base_app_dir).load_content())
      self.extensions = None

      self.wait_for_manual_completion("load_extensions", check_interval=0.1)

      # ... (rest of the initialization)

      self.backend: IBackend = start_backend(self.settings)
      self.backend_stop_event: threading.Event = threading.Event()
      self.backend_thread: threading.Thread = threading.Thread(target=self.backend.run_infinite,
                                                               args=(self.backend_stop_event,))
      self.backend_thread.start()

    except Exception as e:
      raise Exception("Exception during App initialization") from e

  def set_extensions(self, extensions):
    pass

  # ... (other methods)

  def timer_tick(self, index: int) -> None:
    super().timer_tick(index)
    if index == 0:  # Default 500ms timer
      SignalCache().invoke()

  def close(self) -> None:
    super().close()
    if hasattr(self, "backend_thread") and self.backend_thread.is_alive():
      self.backend_stop_event.set()
      self.backend_thread.join()


if __name__ == "__main__":
  parser = ArgumentParser(description=f"{config.PROGRAM_NAME}")
  parser.add_argument("input", nargs="?", default="", help="Path to the input file.")

  start(App, parser)

  results: str = diagnose_shutdown_blockers(return_result=True)
````

## Naming convention, dependencies and library information
[PEP 8 -- Style Guide for Python Code](https://peps.python.org/pep-0008/#naming-conventions)

For modules I use 'lowercase', classes are 'CapitalizedWords' and functions and methods are 'lower_case_with_underscores'.

### Information
Further details will be added in the full release. The package is designed as a **development toolkit**, not just an application runner. More features like threading, crypto, state validation, and I/O extensions are in the works.

## Contributing

We welcome contributions! Please see our [contributing guidelines](https://github.com/adalfarus/dancer/blob/main/CONTRIBUTING.md) for more details on how you can contribute to dancer.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a pull request

### Aps Build master

You can use the aps_build_master script for your os to make your like a lot easier.
It supports running tests, installing, building and much more as well as chaining together as many commands as you like.

This example runs test, build the project and then installs it
````commandline
call .\aps_build_master.bat 234
````

````shell
sudo apt install python3-pip
sudo apt install python3-venv
chmod +x ./aps_build_master.sh
./aps_build_master.sh 234
````

## License

dancer is licensed under the LGPL-2.1 License - see the [LICENSE](https://github.com/adalfarus/dancer/blob/main/LICENSE) file for details.
