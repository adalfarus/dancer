"""Dancer"""
from packaging.version import Version as _Version, InvalidVersion as _InvalidVersion
from argparse import ArgumentParser as _Ag, Namespace as _Ns
from dataclasses import dataclass as _dataclass
from traceback import format_exc as _format_exc
import requests
import logging
import sys
import os

from . import config, io
from .io import IOManager, ActLogger, get_system, SystemTheme, BaseSystemType

from collections import abc as _a
import typing as _ty


__all__ = ["config", "io", "start", "Frontend", "UpdateResult", "UpdateChecker", "MainClass", "DefaultApp", "DefaultAppTUI", "DefaultServerTUI", "DefaultAppGUI"]
__version__ = "0.0.0.1a1"


class Frontend:
    """Different frontends"""
    TUI = 0
    GUI = 1

@_dataclass  # TODO:
class UpdateResult:
    ...

class UpdateChecker:
    # Flags
    INFORM_ABOUT_UPDATE_INFO_FORMAT: bool = True
    CHECK_FOR_UPDATE: bool = True
    UPDATE_CHECK_REQUEST_TIMEOUT: float = 4.0
    SHOW_UPDATE_TIMEOUT: bool = False
    SHOW_UPDATE_ERROR: bool = False
    SHOW_UPDATE_INFO: bool = True
    SHOW_NO_UPDATE_INFO: bool = False
    def __init__(self, update_check_url: str):
        raise NotImplementedError()

    def get_update_result(self) -> tuple[bool, tuple[str, str, str, str], tuple[str | None, tuple[str, str]], tuple[list[str], str], _a.Callable[[str], _ty.Any]]:
        """
        Checks for an update and returns the result.
        """
        icon: str = "Information"
        title: str = "Title"
        text: str = "Text"
        description: str = "Description"
        checkbox: str | None = None
        checkbox_setting: tuple[str, str] = ("", "")
        standard_buttons: list[str] = ["Ok"]
        default_button: str = "Ok"
        retval_func: _a.Callable[[str], _ty.Any] = lambda button: None
        do_popup: bool = True

        try:  # Get update content
            response: requests.Response = requests.get(
                self.update_check_url,
                timeout=float(self.UPDATE_CHECK_REQUEST_TIMEOUT))
        except requests.exceptions.Timeout:
            title, text, description = "Update Info", ("The request timed out.\n"
                                                       "Please check your internet connection, "
                                                       "and try again."), _format_exc()
            standard_buttons, default_button = ["Ok"], "Ok"
            checkbox, checkbox_setting = "Do not show again", ("auto", "show_update_timeout")
            show_update_timeout: bool = self.SHOW_UPDATE_TIMEOUT
            if not show_update_timeout:
                do_popup = False
            return (do_popup,
                    (icon, title, text, description),
                    (checkbox, checkbox_setting),
                    (standard_buttons, default_button), retval_func)
        except requests.exceptions.RequestException:
            title, text, description = "Update Info", ("There was an error with the request.\n"
                                                       "Please check your internet connection and antivirus, "
                                                       "and try again."), _format_exc()
            standard_buttons, default_button = ["Ok"], "Ok"
            return (do_popup,
                    (icon, title, text, description),
                    (checkbox, checkbox_setting),
                    (standard_buttons, default_button), retval_func)
        except Exception as e:
            return (self.SHOW_UPDATE_ERROR,
                    ("Warning", "Update check failed", "Due to an internal error,\nthe operation could not be completed.", _format_exc()),
                    ("Do not show again", ("auto", "show_update_error")),
                    (["Ok"], "Ok"), lambda button: None)

        try:  # Parse update content
            update_json: dict = response.json()
            current_version = _Version(f"{config.VERSION}{config.VERSION_ADD}")
            found_version: _Version | None = None
            found_release: dict | None = None
            found_push: bool = False

            for release in update_json["versions"]:
                release_version = _Version(release["versionNumber"])
                if release_version == current_version:
                    found_version = release_version
                    found_release = release
                    found_push = False  # Doesn't need to be set again
                if release_version > current_version:
                    push = release["push"].title() == "True"
                    if found_version is None or (release_version > found_version and push):
                        found_version = release_version
                        found_release = release
                        found_push = push
                # if found_release and found_version != current_version:
                #     raise NotImplementedError
        except (requests.exceptions.JSONDecodeError, _InvalidVersion, NotImplementedError):
            icon = "Information"  # Reset everything to default, we don't know when the error happened
            title, text, description = "Update Info", "There was an error when decoding the update info.", _format_exc()
            checkbox, checkbox_setting = None, ("", "")
            standard_buttons, default_button = ["Ok"], "Ok"
            retval_func = lambda button: None
            return (do_popup,
                    (icon, title, text, description),
                    (checkbox, checkbox_setting),
                    (standard_buttons, default_button), retval_func)

        show_update_info: bool = self.SHOW_UPDATE_INFO
        show_no_update_info: bool = self.SHOW_NO_UPDATE_INFO

        if found_version != current_version and show_update_info and found_push:
            title = "There is an update available"
            text = (f"There is a newer version ({found_version}) "
                    f"available.\nDo you want to open the link to the update?")
            description = str(found_release.get("description"))  # type: ignore
            checkbox, checkbox_setting = "Do not show again", ("auto", "show_update_info")
            standard_buttons, default_button = ["Yes", "No"], "Yes"

            def retval_func(button: str) -> None:
                """TBA"""
                if button == "Yes":
                    url = str(found_release.get("updateUrl", "None"))  # type: ignore
                    if url.title() == "None":
                        link = update_json["metadata"].get("sorryUrl", "https://example.com")
                    else:
                        link = url
                    self.open_url(link)
        elif show_no_update_info and found_version <= current_version:
            title = "Update Info"
            text = (f"No new updates available.\nChecklist last updated "
                    f"{update_json['metadata']['lastUpdated'].replace('-', '.')}.")
            description = f" --- v{found_version} --- \n{found_release.get('description')}"  # type: ignore
            checkbox, checkbox_setting = "Do not show again", ("auto", "show_no_update_info")
        elif show_no_update_info and not found_push:
            title = "Info"
            text = (f"New version available, but not recommended {found_version}.\n"
                    f"Checklist last updated {update_json['metadata']['lastUpdated'].replace('-', '.')}.")
            description = str(found_release.get("description"))  # type: ignore
            checkbox, checkbox_setting = "Do not show again", ("auto", "show_no_update_info")
        else:
            title, text, description = "Update Info", "There was a logic-error when checking for updates.", ""
            do_popup = False
        return (do_popup,
                (icon, title, text, description),
                (checkbox, checkbox_setting),
                (standard_buttons, default_button), retval_func)

    def show_update_result(self, update_result: tuple[bool, tuple[str, str, str, str], tuple[str | None, tuple[str, str]], tuple[list[str], str], _a.Callable[[str], _ty.Any]]) -> None:
        """
        Shows update result using a message box
        """
        (do_popup,
         (icon, title, text, description),
         (checkbox, checkbox_setting),
         (standard_buttons, default_button), retval_func) = update_result
        if do_popup:
            retval, checkbox_checked = self.prompt_user(title, text, description, icon, standard_buttons,
                                                        default_button, checkbox)
            retval_func(retval)
            if checkbox is not None and checkbox_checked:
                setattr(self, checkbox_setting[1].upper(), False)

class MainClass(_ty.Protocol):
    """
    The main class that gets executed in the application lifecycle.

    This protocol defines the core structure for running an application, handling execution,
    cleanup, and crash-related behavior.
    """
    def __init__(self, parsed_args: _Ns, logging_level: int) -> None: ...
    def exec(self) -> int:
        """
        Execute the application logic.

        This method blocks until the application is complete.

        Returns:
            int: An integer error code indicating the exit status of the application.
        """
        raise NotImplementedError()
    def close(self) -> None:
        """
        Clean up resources after application execution or a crash.

        This will be called after `exec()` completes or a crash occurs to ensure
        all resources are properly released.
        """
        raise NotImplementedError()
    def crash(self, error_title: str, error_text: str, error_description: str) -> bool:
        """
        Handle application crash behavior.

        This method is called after a crash occurs to display or log crash-related
        information. It typically prompts the user whether to restart the application.

        Args:
            error_title (str): A short title summarizing the error.
            error_text (str): A brief message describing the error.
            error_description (str): A detailed explanation of the error.

        Returns:
            bool: True if the application should restart; False otherwise.
        """
        raise NotImplementedError()
    def prompt_user(self, title: str, message: str, details: str,
                    level: _ty.Literal["debug", "information", "question", "warning", "error"],
                    options: list[str], default_option: str, checkbox_label: str | None = None) -> tuple[str | None, bool]:
        """
        Display a prompt to the user with a message, optional checkbox, and buttons to choose from.

        This method can be used to display critical information, questions, or warnings, and
        allows the user to choose a predefined action. An optional checkbox can also be displayed
        (e.g., "Don't show this again").

        Args:
            title (str): The window or dialog title.
            message (str): A short message to show to the user.
            details (str): A more detailed description to accompany the message.
            level (Literal): The level of the user action (e.g., "information", "warning", "question", etc.).
            options (list[str]): A list of button labels representing user actions.
            default_option (str): The default button/action that will be preselected.
            checkbox_label (str | None): The label for an optional checkbox; if None, no checkbox is shown.

        Returns:
            tuple[str | None, bool]: A tuple containing the selected action (or None if no selection was made),
            and a boolean indicating whether the checkbox was activated (True) or not (False).
        """
        raise NotImplementedError()

class DefaultApp(MainClass):
    def __init__(self, parsed_args: _Ns, logging_level: int, /, setup_thread_pool: bool = False):
        try:
            self.pool: LazyDynamicThreadPoolExecutor | None = None
            self._for_loop_list: ThreadSafeList | None = None
            self.max_collections_per_timer_tick: int = 5
            if setup_thread_pool:
                # Thread pool
                self.pool = LazyDynamicThreadPoolExecutor(0, 2, 1.0, 1)
                self._for_loop_list: list[tuple[_ty.Callable[[_ty.Any], _ty.Any], tuple[_ty.Any]]] = ThreadSafeList()
        except Exception as e:
            raise Exception("Exception occurred during initialization of the Main class") from e

    def _check_pool(self) -> bool:
        return self.pool is None or self._for_loop_list is None

    def _ensure_pool(self) -> None:
        if not self._check_pool():
            raise RuntimeError("Pool or/and for loop list is/are not initialized")

    def offload_work(self, task_name: str, task_collection_func: _a.Callable, task: _a.Callable[[], tuple[...]]) -> None:
        self._ensure_pool()
        self.pool.submit(lambda:
                             self._for_loop_list.append(
                                 (task_name, task_collection_func, task())
                             )
                         )

    def wait_for_completion(self, task_name: str, /, check_interval: float = 1.0) -> None:
        self._ensure_pool()
        while any(x[0] == task_name for x in self._for_loop_list):
            time.sleep(check_interval)

    def timer_tick(self) -> None:
        if self._check_pool():
            num_handled: int = 0
            while len(self.for_loop_list) > 0 and num_handled < self.max_collections_per_timer_tick:
                entry = self.for_loop_list.pop()
                name, func, args = entry
                func(*args)
                num_handled += 1

    def close(self) -> None:
        if hasattr(self, "pool"):
            self.pool.shutdown()

class DefaultAppTUI(DefaultApp):
    def __init__(self, log_filepath: str, parsed_args: _Ns, logging_level: int, /, setup_thread_pool: bool = False) -> None:
        super().__init__(parsed_args, logging_level, setup_thread_pool=setup_thread_pool)
        try:
            # Setup ActLogger
            self.logger: ActLogger = ActLogger(log_to_file=True, filepath=log_filepath)
            sys.stdout = self.logger.create_pipe_redirect(sys.stdout, level=logging.DEBUG)
            sys.stderr = self.logger.create_pipe_redirect(sys.stderr, level=logging.ERROR)
            if logging_level:
                mode = getattr(logging, logging.getLevelName(logging_level).upper())
            else:
                mode = logging.INFO
            if mode is not None:
                self.logger.setLevel(mode)
            for exported_line in config.exported_logs.split("\n"):
                self.logger.debug(exported_line)  # Flush config prints

            self.system: BaseSystemType = get_system()
        except Exception as e:
            raise Exception("Exception occurred during initialization of the Main class") from e

    def close(self) -> None:
        if hasattr(self, "logger"):
            sys.stdout = self.logger.restore_pipe(sys.stdout)
            sys.stderr = self.logger.restore_pipe(sys.stderr)

    def crash(self, error_title: str, error_text: str, error_description: str) -> bool:
        return self.prompt_user(f"--- {error_title} ---", error_text + "Do you want to restart?", error_description, options=["Y", "N"], default_option="Y") == "Y"

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

class DefaultAppGUI(DefaultApp):
    def __init__(self, logs_directory: str, parsed_args: _Ns, logging_level: int, /, setup_thread_pool: bool = False) -> None:
        super().__init__(parsed_args, logging_level, setup_thread_pool=setup_thread_pool)
        try:
            self.update_check_url: str = update_check_url
            # Setup IOManager
            self.io_manager: IOManager = IOManager()
            self.io_manager.init(self.prompt_user, logs_directory, config.INDEV)
            if logging_level:
                mode = getattr(logging, logging.getLevelName(logging_level).upper())
            else:
                mode = logging.INFO
            if mode is not None:
                self.io_manager.set_logging_level(mode)
            for exported_line in config.exported_logs.split("\n"):
                self.io_manager.debug(exported_line)  # Flush config prints

            self.system: BaseSystemType = get_system()
            self.os_theme: SystemTheme = self.get_os_theme()
            self.update_theme(self.os_theme)

            if self.INFORM_ABOUT_UPDATE_INFO_FORMAT:
                print("INFORMATION ABOUT UPDATE INFO FORMAT:: https://raw.githubusercontent.com/Giesbrt/Automaten/main/meta/update_check.json")
            if self.CHECK_FOR_UPDATE:
                result = self.get_update_result()
                self.show_update_result(result)
        except Exception as e:
            raise Exception("Exception occurred during initialization of the Main class") from e

    def open_url(self, url: str) -> None:
        raise NotImplementedError()

    def get_os_theme(self) -> SystemTheme:
        """Gets the os theme based on a number of parameters, like environment variables."""
        base = self.system.get_system_theme()
        if not base:
            raw_fallback = str(os.environ.get("DANCER_BACKUP_THEME")).lower()  # Can return None
            fallback = {"light": SystemTheme.LIGHT, "dark": SystemTheme.DARK}.get(raw_fallback)
            if fallback is None:
                return SystemTheme.LIGHT
            return fallback
        return base

    def update_theme(self, new_theme: SystemTheme) -> None:
        self.os_theme = new_theme

    def timer_tick(self) -> None:
        super().timer_tick()
        new_theme = self.get_os_theme()
        if new_theme != self.os_theme:
            self.update_theme(new_theme)
        self.io_manager.invoke_prompts()

def start(frontend: int, main_class: _ty.Type[MainClass], arg_parser: _Ag | None = None, EXIT_CODES: dict[int, _a.Callable[[], None]] | None = None) -> None:
    """Starts the app and handles error catching"""
    if EXIT_CODES is None:
        EXIT_CODES = {
        1000: lambda: os.execv(sys.executable, [sys.executable] + sys.argv[1:])  # RESTART_CODE (only works compiled)
    }
    if arg_parser is None:
        arg_parser = _Ag(description=f"{config.PROGRAM_NAME}")
    dp_app: MainClass | None = None
    current_exit_code: int = -1

    arg_parser.add_argument("--logging-level", choices=["DEBUG", "INFO", "WARN", "WARNING", "ERROR"], default="INFO",
                        help="Logging level (default: INFO)")
    arg_parser.add_argument("--version", action="store_true", help="Shows the version of the program and dancer")
    args = arg_parser.parse_args()

    if args.version:
        print(f"Dancer {__version__} running {config.PROGRAM_NAME} {config.get_version_str()}")
        return

    logging_level_str: str = args.logging_level
    logging_level: int | None = None
    logging_level = getattr(logging, logging_level_str.upper(), None)
    if logging_level is None:
        logging.error(f"Invalid logging mode: {logging_level_str}")
        logging_level = logging.INFO

    print(f"Starting {config.PROGRAM_NAME} {str(config.VERSION) + config.VERSION_ADD} with py{'.'.join([str(x) for x in sys.version_info])} ...")
    try:
        dp_app = main_class(args, logging_level)
        current_exit_code = dp_app.exec()
    except Exception as e:
        perm_error = False
        if isinstance(e.__cause__, PermissionError):
            perm_error = True
        if perm_error:
            error_title = "Warning"
            error_text = (f"{config.PROGRAM_NAME} encountered a permission error. This error is unrecoverable.     \n"
                          "Make sure no other instance is running and that no internal app files are open.     ")
        else:
            error_title = "Fatal Error"
            error_text = (f"There was an error while running the app {config.PROGRAM_NAME}.\n"
                          "This error is unrecoverable.\n"
                          "Please submit the details to our GitHub issues page.")
        error_description = _format_exc()

        if dp_app is not None:
            should_restart: bool = dp_app.crash(error_title, error_text, error_description)
            if should_restart:
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
        # results: str = diagnose_shutdown_blockers(return_result=True)
        EXIT_CODES.get(current_exit_code, lambda: sys.exit(current_exit_code))()
