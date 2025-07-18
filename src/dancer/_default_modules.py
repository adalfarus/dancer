"""Default modules used in apps"""
from dataclasses import dataclass
import logging
import sys
import time
import json
from traceback import format_exc as _format_exc
import os

from packaging.version import Version as _Version, InvalidVersion as _InvalidVersion
import requests
from aplustools.io import SingletonMeta
from aplustools.io.fileio import os_open

from . import config, io

from collections import abc as _a
import typing as _ty

__all__ = ["DefaultLogger", "AdvancedLogger", "Offloader", "UpdateResult", "UpdateChecker", "Translator", "Translation"]


def DefaultLogger(log_filepath: str | None, logging_level: int) -> io.ActLogger:
    """Returns a configured ActLogger instance"""
    # Setup ActLogger
    logger: io.ActLogger
    if log_filepath is not None:
        logger = io.ActLogger(log_to_file=True, filepath=log_filepath)
    else:
        logger = io.ActLogger()
    sys.stdout = logger.create_pipe_redirect(sys.stdout, level=logging.DEBUG)
    sys.stderr = logger.create_pipe_redirect(sys.stderr, level=logging.ERROR)
    mode = getattr(logging, logging.getLevelName(logging_level).upper())
    if mode is not None:
        logger.setLevel(mode)
    for exported_line in config.exported_logs.split("\n"):
        logger.debug(exported_line)  # Flush config prints
    return logger

def AdvancedLogger(logs_directory: str | None, prompt_user: _a.Callable, logging_level: int) -> io.IOManager:
    """Returns a configured IOManager instance, this internally uses ActLogger and ActLogger is Singleton"""
    # Setup IOManager
    io_manager: io.IOManager = io.IOManager()
    if logs_directory is not None:
        io_manager.init(prompt_user, logs_directory, config.INDEV)
    else:
        raise NotImplementedError("Not logging to a directory is not yet supported for IOManager")
    mode = getattr(logging, logging.getLevelName(logging_level).upper())
    if mode is not None:
        io_manager.set_logging_level(mode)
    for exported_line in config.exported_logs.split("\n"):
        io_manager.debug(exported_line)  # Flush config prints
    return io_manager

class Offloader:
    """TBA"""
    def __init__(self) -> None:
        from aplustools.io.concurrency import LazyDynamicThreadPoolExecutor, ThreadSafeList
        self.pool: LazyDynamicThreadPoolExecutor = LazyDynamicThreadPoolExecutor(0, 2, 1.0, 1)
        self._for_loop_list: list[tuple[_ty.Callable[[_ty.Any], _ty.Any], tuple[_ty.Any]]] = ThreadSafeList()
        self._running_tasks: set[str] = set()
        self.max_collections_per_timer_tick: int = 5

    def _check_pool(self) -> bool:
        return not (self.pool is None or self._for_loop_list is None)

    def _ensure_pool(self) -> None:
        if not self._check_pool():
            raise RuntimeError("Pool or/and for loop list is/are not initialized")

    def offload_work(self, task_name: str, task_collection_func: _a.Callable, task: _a.Callable[[], tuple[...]]) -> None:
        self._ensure_pool()
        if task_name in self._running_tasks:
            raise RuntimeError(f"Cannot have two tasks with the name '{task_name}' running at the same time.")
        self._running_tasks.add(task_name)
        self.pool.submit(lambda:
                             self._for_loop_list.append(
                                 (task_name, task_collection_func, task())
                             )
                         )

    def wait_for_completion(self, task_name: str, /, check_interval: float = 1.0) -> None:
        self._ensure_pool()
        while task_name in self._running_tasks:
            time.sleep(check_interval)

    def wait_for_manual_completion(self, task_name: str, /, check_interval: float = 1.0) -> None:
        self._ensure_pool()
        while task_name in self._running_tasks:
            time.sleep(check_interval)
            if self._for_loop_list:
                entry = self._for_loop_list.pop()
                name, func, args = entry
                func(*args)
                self._running_tasks.remove(name)

    def tick(self) -> None:
        ...

    def shutdown(self, wait: bool = True, *, cancel_futures: bool = False) -> None:
        self.pool.shutdown(wait, cancel_futures=cancel_futures)

@dataclass  # TODO:
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


            # self.update_check_url: str = update_check_url  # TODO: Create class UpdateChecker
            # if self.INFORM_ABOUT_UPDATE_INFO_FORMAT:
            #     print("INFORMATION ABOUT UPDATE INFO FORMAT:: https://raw.githubusercontent.com/Giesbrt/Automaten/main/meta/update_check.json")
            # if self.CHECK_FOR_UPDATE:
            # result = self.get_update_result()
            # self.show_update_result(result)

class Translation(metaclass=SingletonMeta): ...

class Translator(metaclass=SingletonMeta):
    def __init__(self, localisation_dir: str) -> None:
        self.localisation_dir: str = localisation_dir
        self.localisations: dict[str, str] = {}
        self._tr: _ty.Type[Translation] | None = None
        self.loaded_localisation: str = ""
        self.reload_localisations()

    def reload_localisations(self) -> None:
        self.localisations.clear()
        for file in os.listdir(self.localisation_dir):
            self.localisations[file.removesuffix(".json")] = file
        return None

    def set_translation_cls(self, translation_cls: _ty.Type[Translation]) -> None:
        if not issubclass(translation_cls, Translation):
            raise ValueError(f"The parameter translation_cls needs to be of type Translation")
        self._tr = translation_cls

    def check_localisations(self) -> None:
        current_localisation: str = self.loaded_localisation
        for localisation in self.localisations.keys():
            self.load(localisation)
        self.load(current_localisation)
        return None

    def load(self, localisation: str) -> None:
        file: str | None = self.localisations.get(localisation)
        if file is None:
            raise ValueError(f"The localisation for '{localisation}' is not currently loaded")
        filepath: str = os.path.join(self.localisation_dir, file)

        translation: dict[str, str]
        with os_open(filepath, "r") as f:
            try:
                translation = json.loads(f.read())
            except json.JSONDecodeError as e:
                raise RuntimeError(f"Failed to parse localisation file '{filepath}'") from e

        if self._tr is None:
            raise RuntimeError("You need to set self.tr before you can load a translation. "
                               "Tr exists to enable type hinting.")

        keys: set[str] = set()
        keys.update(dir(self._tr))
        keys.update(self._tr.__annotations__.keys())

        for key in keys:
            if not key.startswith("_"):
                value: str | None = translation.get(key)
                if value is None:
                    raise RuntimeError(f"The key '{key}' was not provided by the translation for '{localisation}'")
                setattr(self._tr, key, value)
        self.loaded_localisation = localisation
        return None
