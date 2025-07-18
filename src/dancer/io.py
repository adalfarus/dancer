"""IO Component of dancer"""
from pathlib import Path as PLPath
import logging
import sys
import re
import io
import os

from aplustools.data import SingletonMeta
from aplustools.io.env import BaseSystemType, SystemTheme, get_system

# Standard typing imports for aps
import collections.abc as _a
import typing as _ty
import types as _ts

__all__ = ["BaseSystemType", "SystemTheme", "get_system", "SingletonMeta", "ActLogger", "IOManager"]


# Copyright adalfarus
# Helper class to redirect streams to the logger
class _StreamToLogger(io.IOBase):
    """
    File-like object that redirects writes to a logger instance.
    """

    def __init__(self, logger, log_level, original_stream: _ty.IO):
        """
        Initialize the stream redirection.

        :param logger: Logger instance where messages will be redirected.
        :param log_level: Logging level for the redirected messages.
        """
        self.logger = logger
        self.log_level = log_level
        self.original_stream = original_stream
        self.linebuf = ""

    def write(self, buf):
        """
        Write method for the file-like object.

        :param buf: String to write.
        """
        self.linebuf += buf
        while "\n" in self.linebuf:
            line, self.linebuf = self.linebuf.split("\n", 1)
            if line:
                self.logger.log(self.log_level, line)
            else:
                # Handle empty lines (e.g., when there are multiple newlines)
                self.logger.log(self.log_level, "")

    def flush(self):
        """
        Flush method for file-like object.
        """
        if self.linebuf:
            self.logger.log(self.log_level, self.linebuf.rstrip())
            self.linebuf = ""

    def restore(self) -> io.IOBase:
        return self.original_stream

# Copyright adalfarus
class ActLogger(metaclass=SingletonMeta):
    """
    A configurable logger for ActFramework that supports logging to both the console
    and an optional log file. It provides methods to log messages at different
    logging levels and can monitor and redirect system output streams.

    Attributes:
        _logger: The logger instance used for logging messages.
        handlers: A list of handlers attached to the logger (console, file handlers).
    """
    def __init__(self, name: str = "ActLogger", log_to_file: bool = False, filepath: str | PLPath = "app.log") -> None:
        """
        Initialize the act logger.

        :param name: Name of the logger.
        :param log_to_file: Boolean indicating if logs should be written to a file.
        :param filepath: Path of the log file.
        """
        self._logger = logging.getLogger(name)
        self._logger.setLevel(logging.DEBUG)
        self.handlers: list[logging.Handler] = []

        # Create formatter with the desired format
        formatter = logging.Formatter(
            '[%(asctime)s.%(msecs)03d] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Console handler
        console_handler = logging.StreamHandler(sys.__stdout__)
        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)
        self.handlers.append(console_handler)

        # File handler (optional)
        if log_to_file:
            file_handler = logging.FileHandler(filepath, encoding='utf8')
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)
            self.handlers.append(file_handler)
        self.logging_level: int = -1

    def create_pipe_redirect(self, pipe: _ty.IO, level: int = logging.INFO) -> _StreamToLogger:
        """
        Return a stream wrapper that redirects writes to the logger.

        :param pipe: The original stream (e.g., sys.stdout, a file, etc.)
        :param level: Logging level to use
        :return: _StreamToLogger instance
        """
        return _StreamToLogger(self._logger, level, pipe)

    def restore_pipe(self, replacement: _StreamToLogger) -> io.IOBase:
        """
        Restore the given global pipe (e.g. sys.stdout) to its original value.

        :param replacement: The _StreamToLogger that was used to override it.
        """
        return replacement.restore()

    def add_handler(self, mirror_to_io: logging.Handler) -> None:
        """Adds a handler to the underlying logger and keeps track of it in the .handlers attribute"""
        self.handlers.append(mirror_to_io)
        self._logger.addHandler(mirror_to_io)

    def log(self, level: int, message: str) -> None:
        """Log a message with a specific logging level."""
        self._logger.log(level, message)

    # Convenience methods for different logging levels
    def info(self, message: str) -> None:
        """
        Log an informational message.

        :param message: The message to log at the INFO level. Typically used for
                        general application progress or operational messages.
        """
        self._logger.info(message)

    def debug(self, message: str) -> None:
        """
        Log a debug message.

        :param message: The message to log at the DEBUG level. Typically used for
                        detailed information useful for diagnosing issues or tracing execution flow.
        """
        self._logger.debug(message)

    def error(self, message: str) -> None:
        """
        Log an error message.

        :param message: The message to log at the ERROR level. Typically used to
                        indicate a significant issue or error in the application.
        """
        self._logger.error(message)

    def warning(self, message: str) -> None:
        """
        Log a warning message.

        :param message: The message to log at the WARNING level. Typically used to
                        indicate a slight issue or warn about an action.
        :return:
        """
        self._logger.warning(message)

    def setLevel(self, logging_level: int) -> None:
        """Sets the level of the underlying logger"""
        self._logger.setLevel(logging_level)
        self.logging_level = logging_level

# Copyright zScout
T = _ty.TypeVar("T")
class OrderedSet(_ty.Generic[T]):
    # Docs generated with Github Copilot
    def __init__(self, iterable: _ty.Iterable[_ty.Any] | None = None) -> None:
        """
        OrderedSet is a hybrid of list and set. It maintains the order of elements like a list and ensures that each
        element is unique like a set. It is implemented using a list and a set. The list maintains the order of elements
        and the set ensures that each element is unique. The list is used to maintain the order of elements and the set is
        used to check if an element is already present in the OrderedSet."""
        self._items: list[T] = []
        self._seen: set[T] = set()
        if iterable:
            for item in iterable:
                self.add(item)

    def add(self, item: T) -> None:
        """
        Adds an item to the OrderedSet if it is not already present in the OrderedSet.
        :param item: The item to be added to the OrderedSet.
        :return: None
        """
        if item not in self._seen:
            self._items.append(item)
            self._seen.add(item)

    def discard(self, item: T) -> None:
        """
        Removes an item from the OrderedSet if it is present in the OrderedSet.
        :param item: The item to be removed from the OrderedSet.
        :return: None
        """
        if item in self._seen:
            self._items.remove(item)
            self._seen.remove(item)

    def remove(self, item: T) -> None:
        """
        Removes an item from the OrderedSet if it is present in the OrderedSet. If the item is not present in the
        OrderedSet, a KeyError is raised.
        :param item: The item to be removed from the OrderedSet.
        :return: None
        """
        if item not in self._seen:
            raise KeyError(f"{item} not in OrderedSet")
        self.discard(item)

    def clear(self) -> None:
        """
        Removes all items from the OrderedSet.
        :return: None
        """
        self._items.clear()
        self._seen.clear()

    def get_index(self, item: T) -> int:
        """
        Returns the index of an item in the OrderedSet.
        :param item: The item whose index is to be returned.
        :return: The index of the item in the OrderedSet.
        """
        return self._items.index(item)

    def get_by_index(self, index: int) -> T:
        """
        Returns the item at a given index in the OrderedSet.
        :param index: The index of the item to be returned.
        :return: The item at the given index in the OrderedSet.
        """
        return self._items[index]

    def to_list(self) -> list[T]:
        """
        Returns the items in the OrderedSet as a list.
        :return: The items in the OrderedSet as a list.
        """
        return self._items

    def to_set(self) -> set[T]:
        """
        Returns the items in the OrderedSet as a set.
        :return: The items in the OrderedSet as a set.
        """
        return self._seen

    @staticmethod
    def from_list(lst: _ty.List[T]) -> 'OrderedSet':
        return OrderedSet(lst)

    @staticmethod
    def from_set(st: _ty.Set[T]) -> 'OrderedSet':
        return OrderedSet(st)

    def __len__(self):
        """
        Returns the number of items in the OrderedSet.
        :return: The number of items in the OrderedSet.
        """
        return len(self._items)

    def __iter__(self):
        """
        Returns an iterator over the items in the OrderedSet.
        :return: An iterator over the items in the OrderedSet.
        """
        return iter(self._items)

    def __contains__(self, item: T):
        """
        Returns True if an item is present in the OrderedSet, False otherwise.
        :param item: The item to be checked for presence in the OrderedSet.
        :return: True if the item is present in the OrderedSet, False otherwise.
        """
        return item in self._seen

    def __repr__(self):
        """
        Returns a string representation of the OrderedSet.
        :return: A string representation of the OrderedSet.
        """
        return f"OrderedSet({self._items})"

    def __eq__(self, other):
        """
        Returns True if the OrderedSet is equal to another OrderedSet, False otherwise.
        :param other: The other OrderedSet to be compared with.
        :return: True if the OrderedSet is equal to the other OrderedSet, False otherwise.
        """
        if isinstance(other, OrderedSet):
            return self._items == other._items
        return False

    def __or__(self, other):
        """
        Returns the union of the OrderedSet with another OrderedSet or set.
        :param other: The other OrderedSet or set to be unioned with.
        :return: The union of the OrderedSet with the other OrderedSet or set.
        """
        if not isinstance(other, (OrderedSet, set)):
            return NotImplemented
        return OrderedSet(self._items + [item for item in other if item not in self])

    def __and__(self, other):
        """
        Returns the intersection of the OrderedSet with another OrderedSet or set.
        :param other: The other OrderedSet or set to be intersected with.
        :return: The intersection of the OrderedSet with the other OrderedSet or set.
        """
        if not isinstance(other, (OrderedSet, set)):
            return NotImplemented
        return OrderedSet(item for item in self if item in other)

    def __sub__(self, other):
        """
        Returns the difference of the OrderedSet with another OrderedSet or set.
        :param other: The other OrderedSet or set to be differenced with.
        :return: The difference of the OrderedSet with the other OrderedSet or set.
        """
        if not isinstance(other, (OrderedSet, set)):
            return NotImplemented
        return OrderedSet(item for item in self if item not in other)

# Copyright zScout
S = _ty.TypeVar("S")
class StaticContainer(_ty.Generic[S]):
    def __init__(self, value: S | None = None) -> None:
        self._value: S | None = value

    # TODO: self._value is S or None but returned it is just S?
    def get_value(self) -> S:
        """
        Get the value stored in the Container
        :return: (S) returns the current value stored
        """
        return self._value

    def set_value(self, new_value: S) -> None:
        """
        Sets a new value to store in the Container
        :param new_value: S
        :return: None
        """
        self._value = new_value

    def has_value(self) -> bool:
        """
        Returns a bool to indicate if the container stores a value
        :return: Srue, if the Container stores a value
        """
        return self._value is not None

    def clear_value(self) -> None:
        """
        Clears the value stored
        :return: None
        """
        self._value = None

# Copyright zScout  TODO: Refactor, title etc are just wrongly ordered in the methods and adding support for custom icons; Or also ignoring msgs with only small changes?
class IOManager(metaclass=SingletonMeta):
    """TBA"""
    _do_not_show_again: OrderedSet[str] = OrderedSet()
    _currently_displayed: OrderedSet[str] = OrderedSet()
    _button_display_callable: StaticContainer[_ty.Callable] = StaticContainer()
    _is_indev: StaticContainer[bool] = StaticContainer()
    _popup_queue: _ty.List[_ty.Callable[[_ty.Any], _ty.Any]] = []

    _logger: ActLogger

    def add_handler(self, handler) -> None:
        self._logger.add_handler(handler)

    def has_cached_errors(self) -> bool:
        """
        Returns if there are popups cached which have not been displayed yet
        :return: bool
        """
        return len(self._popup_queue) > 0

    def invoke_prompts(self) -> None:
        """

        :return:
        """
        if not self.has_cached_errors():
            return

        popup_callable: _ty.Callable = self._popup_queue[0]
        self._popup_queue.pop(0)

        popup_callable()

    def init(self, promt_creation_callable: _ty.Callable, logs_folder_path: str, is_indev: bool) -> None:
        """
        Initializes the ErrorCache with a popup creation callable and development mode flag.
        :param promt_creation_callable: Callable used to create popups.
        :param logs_folder_path: File path to the logs folder.
        :param is_indev: Boolean indicating whether the application is in development mode.
        :return: None
        """
        self._button_display_callable.set_value(promt_creation_callable)
        self._order_logs(logs_folder_path)
        self._logger = ActLogger(log_to_file=True, filepath=os.path.join(logs_folder_path, "latest.log"))
        sys.stdout = self._logger.create_pipe_redirect(sys.stdout, level=logging.DEBUG)
        sys.stderr = self._logger.create_pipe_redirect(sys.stderr, level=logging.ERROR)
        # Replace fancy characters
        self._is_indev.set_value(is_indev)

    def set_logging_level(self, level: int) -> None:
        """
        Sets the logging level of the Logger
        :param level: Logging level to set to.
        :return: None
        """
        self._logger.setLevel(level)

    def get_logging_level(self) -> int:
        return self._logger.logging_level

    @staticmethod
    def _order_logs(directory: str) -> None:
        logs_dir = PLPath(directory)
        to_log_file = logs_dir / "latest.log"

        if not to_log_file.exists():
            print("Logfile missing")
            return

        with open(to_log_file, "rb") as f:
            # (solution from https://stackoverflow.com/questions/46258499/how-to-read-the-last-line-of-a-file-in-python)
            first_line = f.readline().decode()
            try:  # catch OSError in case of a one line file
                f.seek(-2, os.SEEK_END)
                while f.read(1) != b"\n":
                    f.seek(-2, os.SEEK_CUR)
            except OSError:
                f.seek(0)
            last_line = f.readline().decode()

        try:
            date_pattern = r"^[\[(](\d{4}-\d{2}-\d{2})"
            start_date = re.search(date_pattern, first_line).group(1)  # type: ignore
            end_date = re.search(date_pattern, last_line).group(1)  # type: ignore
        except AttributeError:
            print("Removing malformed latest.log")
            os.remove(to_log_file)
            return

        date_name = f"{start_date}_{end_date}"
        date_logs = list(logs_dir.rglob(f"{date_name}*.log"))

        if not date_logs:
            new_log_file_name = logs_dir / f"{date_name}.log"
        else:
            try:
                max_num = max(
                    (int(re.search(r"#(\d+)$", p.stem).group(1)) for p in date_logs if  # type: ignore
                     re.search(r"#(\d+)$", p.stem)),
                    default=0
                )
            except AttributeError:
                print("AttribError")
                return
            max_num += 1
            base_log_file = logs_dir / f"{date_name}.log"
            if base_log_file.exists():
                os.rename(base_log_file, logs_dir / f"{date_name}#{max_num}.log")
                max_num += 1
            new_log_file_name = logs_dir / f"{date_name}#{max_num}.log"

        os.rename(to_log_file, new_log_file_name)
        print(f"Renamed latest.log to {new_log_file_name}")

    def _show_prompt(self, title: str, text: str, description: str,
                     level: _ty.Literal["debug", "information", "question", "warning", "error"],
                     custom_options: _ty.Dict[str, _ty.Callable] | None = None) -> None:
        """
        Displays a dialog box with the provided information.
        :param title: Title of the dialog box.
        :param text: Main text content of the dialog box.
        :param description: Additional description text.
        :param level: Type of icon to display in the dialog box.
        :return: None
        """
        if text in self._currently_displayed:
            # Error is currently displayed
            return

        if text in self._do_not_show_again:
            # Error should not be displayed again
            return

        if not self._button_display_callable.has_value():
            return

        self._currently_displayed.add(text)

        checkbox_text: str = "Do not show again"
        options_list: _ty.List[str] = ["Ok"]
        default_option: str = options_list[0]

        # add custom buttons
        if custom_options is not None:
            for key in list(custom_options.keys()):
                options_list.append(key)

        popup_creation_callable: _ty.Callable = self._button_display_callable.get_value()
        popup_return: tuple[str | None, bool] = popup_creation_callable(title, text, description, level,  # "[N.E.F.S] " +
                                                                        options_list, default_option, checkbox_text)

        if popup_return[1]:
            self._do_not_show_again.add(text)
        self._currently_displayed.remove(text)

        # invoke button commands
        option_name: str = popup_return[0]
        if custom_options is not None:
            if option_name in custom_options:
                custom_options[option_name]()

    def _handle_prompt(self, show_prompt: bool, title: str, log_message: str, description: str,
                       level: _ty.Literal["debug", "information", "question", "warning", "error"],
                       custom_options: _ty.Dict[str, _ty.Callable] | None = None) -> None:
        """
        Handles the process of displaying a dialog based on parameters.
        :param show_prompt: Boolean indicating whether to show the dialog.
        :param title: Title of the dialog.
        :param log_message: Log message associated with the dialog.
        :param description: Additional description text.
        :param level: Type of icon to display in the dialog.
        :return: None
        """
        if not show_prompt:
            return

        self._popup_queue.append(lambda: self._show_prompt(title, log_message, description, level, custom_options))

    # "Errors"

    def warn(self, log_message: str, description: str = "", show_prompt: bool = False,
             print_log: bool = True, prompt_title: str | None = None,
             custom_options: _ty.Dict[str, _ty.Callable] | None = None) -> None:
        """
        Logs a warning message and optionally displays a warning dialog.
        :param prompt_title: Sets the popup window title
        :param custom_options: Defines additional buttons for the popup window
        :param log_message: The warning message to log.
        :param description: Additional description of the warning.
        :param show_prompt: Whether to show a dialog for the warning.
        :param print_log: Whether to print the log message.
        :return: None
        """
        return self.warning(log_message, description, show_prompt, print_log, prompt_title, custom_options)

    def info(self, log_message: str, description: str = "", show_prompt: bool = False,
             print_log: bool = True, prompt_title: str | None = None,
             custom_options: _ty.Dict[str, _ty.Callable] | None = None) -> None:
        """
        Logs an informational message and optionally displays an information dialog.
        :param log_message: The informational message to log.
        :param description: Additional description of the information.
        :param show_prompt: Whether to show a dialog for the information.
        :param print_log: Whether to print the log message.
        :param prompt_title: Sets the popup window title
        :param custom_options: Defines additional buttons for the popup window
        :return: None
        """
        title: str = "Information"
        if prompt_title is not None:
            title += f": {prompt_title}"

        if print_log:
            self._logger.info(f"{log_message} {f'({description})' if description else ''}")

        if ActLogger().logging_level > logging.INFO:
            return

        self._handle_prompt(show_prompt, title, log_message, description, "information", custom_options)

    def warning(self, log_message: str, description: str = "", show_prompt: bool = False,
                print_log: bool = True, prompt_title: str | None = None,
                custom_options: _ty.Dict[str, _ty.Callable] | None = None) -> None:
        """
        Logs a warning message and optionally displays a warning dialog.
        :param log_message: The warning message to log.
        :param description: Additional description of the warning.
        :param show_prompt: Whether to show a dialog for the warning.
        :param print_log: Whether to print the log message.
        :param prompt_title: Sets the popup window title
        :param custom_options: Defines additional buttons for the popup window
        :return: None
        """
        title: str = "Warning"
        if prompt_title is not None:
            title += f": {prompt_title}"

        if print_log:
            self._logger.warning(f"{log_message} {f'({description})' if description else ''}")

        if ActLogger().logging_level > logging.WARNING:
            return

        self._handle_prompt(show_prompt, title, log_message, description, "warning", custom_options)

    def fatal_error(self, log_message: str, description: str = "", show_prompt: bool = False,
                    print_log: bool = True, prompt_title: str | None = None,
                    custom_options: _ty.Dict[str, _ty.Callable] | None = None) -> None:
        """
        Logs a fatal error message and optionally displays an error dialog.
        :param log_message: The error message to log.
        :param description: Additional description of the error.
        :param show_prompt: Whether to show a dialog for the error.
        :param print_log: Whether to print the log message.
        :param prompt_title: Sets the popup window title
        :param custom_options: Defines additional buttons for the popup window
        :return: None
        """
        self.error(log_message, description, show_prompt, print_log, prompt_title, custom_options, error_severity="FATAL")

    def error(self, log_message: str, description: str = "", show_prompt: bool = False,
              print_log: bool = True, prompt_title: str | None = None,
              custom_options: _ty.Dict[str, _ty.Callable] | None = None, *_,
              error_severity: str = "NORMAL") -> None:
        """
        Logs an error message and optionally displays an error dialog.
        :param log_message: The error message to log.
        :param description: Additional description of the error.
        :param show_prompt: Whether to show a dialog for the error.
        :param print_log: Whether to print the log message.
        :param prompt_title: Sets the popup window title
        :param custom_options: Defines additional buttons for the popup window
        :param error_severity: Defined a custom error name.
        :return: None
        """
        title: str = f"{str(error_severity).capitalize()} Error"
        if prompt_title is not None:
            title += f": {prompt_title}"

        if print_log:
            self._logger.error(f"{str(error_severity)}: {log_message} {f'({description})' if description else ''}")

        if ActLogger().logging_level > logging.ERROR:
            return

        self._handle_prompt(show_prompt, title, log_message, description, "error", custom_options)

    def debug(self, log_message: str, description: str = "", show_prompt: bool = False,
              print_log: bool = True, prompt_title: str | None = None,
              custom_options: _ty.Dict[str, _ty.Callable] | None = None) -> None:
        """
        Logs a debug message and optionally displays a debug dialog, only if in development mode.
        :param log_message: The debug message to log.
        :param description: Additional description of the debug information.
        :param show_prompt: Whether to show a dialog for the debug information.
        :param print_log: Whether to print the log message.
        :param prompt_title: Sets the popup window title
        :param custom_options: Defines additional buttons for the popup window
        :return: None
        """
        if not self._is_indev.has_value():
            return

        INDEV: bool = self._is_indev.get_value()  # config.INDEV
        if not INDEV:
            return

        title: str = "Debug"
        if prompt_title is not None:
            title += f": {prompt_title}"

        if print_log:
            self._logger.debug(f"{log_message} {f'({description})' if description else ''}")

        if ActLogger().logging_level > logging.DEBUG:
            return

        self._handle_prompt(show_prompt, title, log_message, description, "debug", custom_options)

    def prompt_user(self, title: str, message: str, details: str,
                    level: _ty.Literal["debug", "information", "question", "warning", "error"],
                    options: list[str], default_option: str, checkbox_label: str | None = None,
                    return_type: _ty.Literal["thread", "proc"] = "thread"):  # -> tuple[SafeList, Event]:
        raise NotImplementedError("The current implementation does not support user prompting with arbitrary data.")

    def __del__(self) -> None:
        if hasattr(self, "_logger"):
            sys.stdout = self._logger.restore_pipe(sys.stdout)  # type: ignore
            sys.stderr = self._logger.restore_pipe(sys.stderr)  # type: ignore
