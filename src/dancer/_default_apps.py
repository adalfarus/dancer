"""Default app configurations"""
from argparse import Namespace as _Ns
import shutil
import os

from ._app import MainClass
from ._default_modules import DefaultLogger, AdvancedLogger, Offloader
from . import io

from collections import abc as _a
import typing as _ty

__all__ = ["DefaultApp", "DefaultAppTUI", "DefaultServerTUI", "DefaultThemedApp"]


class DefaultApp(MainClass):
    def __init__(self, parsed_args: _Ns, logging_level: int, /, setup_thread_pool: bool = False):
        try:
            self.offloader: Offloader | None = None
            if setup_thread_pool:
                self.offloader = Offloader()
        except Exception as e:
            raise Exception("Exception occurred during initialization of the Main class") from e

    def _ensure_offloader(self) -> None:
        if self.offloader is None:
            raise RuntimeError("Pool or/and for loop list is/are not initialized")

    def offload_work(self, task_name: str, task_collection_func: _a.Callable, task: _a.Callable[[], tuple]) -> None:
        """Offloads work to self.offloader"""
        self._ensure_offloader()
        self.offloader.offload_work(task_name, task_collection_func, task)  # type: ignore

    def wait_for_completion(self, task_name: str, /, check_interval: float = 1.0) -> None:
        """Waits for a task with a certain name to complete"""
        self._ensure_offloader()
        self.offloader.wait_for_completion(task_name, check_interval=check_interval)  # type: ignore

    def wait_for_manual_completion(self, task_name: str, /, check_interval: float = 1.0) -> None:
        """Waits manually for a certain task to complete by working down the task results itself"""
        self._ensure_offloader()
        self.offloader.wait_for_manual_completion(task_name, check_interval=check_interval)  # type: ignore

    def timer_tick(self) -> None:
        """Does stuff that needs to be done periodically"""
        if self.offloader is not None:
            self.offloader.tick()

    def close(self) -> None:
        if hasattr(self, "offloader") and self.offloader is not None:
            self.offloader.shutdown()

class DefaultAppTUI(DefaultApp):
    def __init__(self, log_filepath: str | None, parsed_args: _Ns, logging_level: int, /, setup_thread_pool: bool = False) -> None:
        super().__init__(parsed_args, logging_level, setup_thread_pool=setup_thread_pool)
        try:
            self.logger: io.ActLogger = DefaultLogger(log_filepath, logging_level)
            self.system: io.BaseSystemType = io.get_system()
        except Exception as e:
            raise Exception("Exception occurred during initialization of the Main class") from e

    def close(self) -> None:
        if hasattr(self, "logger"):
            sys.stdout = self.logger.restore_pipe(sys.stdout)  # type: ignore
            sys.stderr = self.logger.restore_pipe(sys.stderr)  # type: ignore

    def crash(self, error_title: str, error_text: str, error_description: str) -> bool:
        return self.prompt_user(f"--- {error_title} ---", error_text + "Do you want to restart?", error_description, "error", options=["Y", "N"], default_option="Y") == "Y"

    def prompt_user(self, title: str, message: str, details: str,
                    level: _ty.Literal["debug", "information", "question", "warning", "error"],
                    options: list[str], default_option: str, checkbox_label: str | None = None) -> tuple[str | None, bool]:
        # Log the message at the appropriate level
        log_func = getattr(self.logger, level if level != "information" else "info", self.logger.info)
        log_func(f"{title} | {message}\n{details}")

        terminal_width = shutil.get_terminal_size((80, 20)).columns

        def print_separator():
            print("-" * terminal_width)

        print_separator()
        print(f"\033[1m{title}\033[0m")  # Bold title
        print_separator()
        print(message)
        print()
        if details:
            print(f"\033[2m{details}\033[0m")  # Dimmed details
        print()

        # Display options
        print("Options:")
        for option in options:
            prefix = "-> " if option == default_option else "   "
            print(f"{prefix}{option}")

        selected_option: str | None = None
        checkbox_checked: bool = False

        while selected_option not in options:
            try:
                user_input = input(f"\nSelect option [{default_option}]: ").strip()
                if user_input == "":
                    selected_option = default_option
                elif user_input in options:
                    selected_option = user_input
                else:
                    print(f"Invalid option. Choose one of: {', '.join(options)}")
            except KeyboardInterrupt:
                print("\nCancelled.")
                return None, False

        if checkbox_label:
            while True:
                checkbox_input = input(f"{checkbox_label} [y/N]: ").strip().lower()
                if checkbox_input in ("y", "yes"):
                    checkbox_checked = True
                    break
                elif checkbox_input in ("n", "no", ""):
                    checkbox_checked = False
                    break
                else:
                    print("Please enter y or n.")

        print_separator()
        print(f"Selected: {selected_option} | {'☑' if checkbox_checked else '☐'} {checkbox_label or ''}")
        print_separator()
        return selected_option, checkbox_checked

class DefaultServerTUI(DefaultAppTUI):
    def __init__(self, log_filepath: str, parsed_args: _Ns, logging_level: int, /, always_restart: bool = False,
                 setup_thread_pool: bool = False) -> None:
        super().__init__(log_filepath, parsed_args, logging_level, setup_thread_pool=setup_thread_pool)
        self.always_restart: bool = always_restart

    def prompt_user(self, title: str, message: str, details: str,
                    level: _ty.Literal["debug", "information", "question", "warning", "error"],
                    options: list[str], default_option: str, checkbox_label: str | None = None) -> tuple[str | None, bool]:
        return None, False

    def crash(self, error_title: str, error_text: str, error_description: str) -> bool:
        print(f"--- {error_title} ---\n{error_text}\n{error_description}")
        # for line in (error_text + error_description).split("\n"):
        #     print(line)
        return self.always_restart

class DefaultThemedApp(DefaultApp):
    def __init__(self, logs_directory: str, parsed_args: _Ns, logging_level: int, /, setup_thread_pool: bool = False) -> None:
        super().__init__(parsed_args, logging_level, setup_thread_pool=setup_thread_pool)
        try:
            self.io_manager: io.IOManager = AdvancedLogger(logs_directory, self.prompt_user, logging_level)

            self.system: io.BaseSystemType = io.get_system()
            self.os_theme: io.SystemTheme = self.get_os_theme()
            self.update_theme(self.os_theme)
        except Exception as e:
            raise Exception("Exception occurred during initialization of the Main class") from e

    def open_url(self, url: str) -> None:
        """Opens the given url in a browser"""
        raise NotImplementedError()

    def get_os_theme(self) -> io.SystemTheme:
        """Gets the os theme based on a number of parameters, like environment variables."""
        base = self.system.get_system_theme()
        if not base:
            raw_fallback = str(os.environ.get("DANCER_BACKUP_THEME")).lower()  # Can return None
            fallback = {"light": io.SystemTheme.LIGHT, "dark":io. SystemTheme.DARK}.get(raw_fallback)
            if fallback is None:
                return io.SystemTheme.LIGHT
            return fallback
        return base

    def update_theme(self, new_theme: io.SystemTheme) -> None:
        """Does tasks that need to be done if the theme changes"""
        self.os_theme = new_theme

    def timer_tick(self) -> None:
        super().timer_tick()
        new_theme = self.get_os_theme()
        if new_theme != self.os_theme:
            self.update_theme(new_theme)
        self.io_manager.invoke_prompts()
