"""Everything around the base app"""
from argparse import ArgumentParser as _Ag, Namespace as _Ns
from traceback import format_exc as _format_exc
import logging
import sys
import os

from . import config

from collections import abc as _a
import typing as _ty


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

def start(main_class: _ty.Type[MainClass], arg_parser: _Ag | None = None, exit_codes: dict[int, _a.Callable[[], None]] | None = None) -> None:
    """Starts the app and handles error catching"""
    if exit_codes is None:
        sys.argv[0] = os.path.join(config.old_cwd, sys.argv[0])
        if config.is_compiled():
            exit_codes = {
                1000: lambda: os.execv(sys.executable, [sys.executable] + sys.argv[1:])  # RESTART_CODE (only works compiled)
            }
        else:
            exit_codes = {
                1000: lambda: os.execv(sys.executable, [sys.executable] + sys.argv)  # RESTART_CODE (only works uncompiled)
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
        from . import __version__
        print(f"Dancer {__version__} running {config.PROGRAM_NAME} {config.get_version_str()}")
        return

    logging_level_str: str = args.logging_level
    logging_level: int
    input_logging_level = getattr(logging, logging_level_str.upper(), None)
    if input_logging_level is None:
        logging.error(f"Invalid logging mode: {logging_level_str}")
        logging_level = logging.INFO
    else:
        logging_level = input_logging_level

    if config.INDEV:
        print("Setting logging level to debug because INDEV flag is set ...")
        logging_level = logging.DEBUG
    print(f"Starting {config.PROGRAM_NAME} {str(config.VERSION) + config.VERSION_ADD} with py{'.'.join([str(x) for x in sys.version_info])} {'[INDEV]' if config.INDEV else ''} ...")
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
        exit_codes.get(current_exit_code, lambda: sys.exit(current_exit_code))()
