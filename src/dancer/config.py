"""Configures your environment"""
from dataclasses import dataclass as _dc
import platform
import shutil
import sys
import os

import typing as _ty
_DirectoryTree = dict[str, _ty.Union["DirectoryTree", None]]

INDEV: bool = False
INDEV_KEEP_RUNTIME_FILES: bool = True
PROGRAM_NAME: str = "ContentView"
VERSION: int = 100
VERSION_ADD: str = "a0"
PROGRAM_NAME_NORMALIZED: str = f"{PROGRAM_NAME.lower().replace(' ', '_')}_{VERSION}{VERSION_ADD}"
OS_LIST: dict[str, dict[str, tuple[str, ...]]] = {"Windows": {"10": ("any",), "11": ("any",)}}
PY_LIST: list[tuple[int, int]] = [(3, 10), (3, 11), (3, 12), (3, 13)]
DIR_STRUCTURE: _DirectoryTree
LOCAL_MODULE_LOCATIONS: list[str]

OLD_CWD: str = os.getcwd()
if "CONFIG_DONE" not in locals():
    CONFIG_DONE: bool = False
if "CHECK_DONE" not in locals():
    CHECK_DONE: bool = False

exported_logs: str
base_app_dir: str
old_cwd: str

exit_code: int
exit_message: str

def is_compiled() -> bool:
    """  # From aps.io.env
    Detects if the code is running in a compiled environment and identifies the compiler used.

    This function checks for the presence of attributes and environment variables specific
    to common Python compilers, including PyInstaller, cx_Freeze, and py2exe.
    :return: bool
    """
    return getattr(sys, "frozen", False) and (hasattr(sys, "_MEIPASS") or sys.executable.endswith(".exe"))

def get_version_str() -> str:
    return str(VERSION) + VERSION_ADD

def _configure() -> dict[str, str]:
    if is_compiled():
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        if not sys.stdout:
            sys.stdout = open(os.devnull, "w")
        if not sys.stderr:
            sys.stderr = open(os.devnull, "w")
    accumulated_logs = "Starting cloning of defaults ...\n"
    old_cwd = os.getcwd()
    install_dir = os.path.join(old_cwd, "default-config")  # TODO: Use systems stuff
    base_app_dir = os.path.join(os.environ.get("LOCALAPPDATA", "."), PROGRAM_NAME_NORMALIZED)

    if INDEV and os.path.exists(base_app_dir):  # Remove everything to simulate a fresh install
        if not INDEV_KEEP_RUNTIME_FILES:
            shutil.rmtree(base_app_dir)
            os.mkdir(base_app_dir)
        else:  # Skip only .db or .log files
            for root, dirs, files in os.walk(base_app_dir, topdown=False):
                for file in files:
                    if not file.endswith((".db", ".log")):
                        os.remove(os.path.join(root, file))
                for directory in dirs:
                    dir_path = os.path.join(root, directory)
                    if not any(f.endswith((".db", ".log")) or os.path.isdir(os.path.join(dir_path, f)) for f in os.listdir(dir_path)):
                        shutil.rmtree(dir_path)

    dirs_to_create = []
    # Use a stack to iteratively traverse the directory structure
    stack: list[tuple[str, _DirectoryTree]] = [(base_app_dir, DIR_STRUCTURE)]
    while stack:
        current_base, subtree = stack.pop()
        for name, children in subtree.items():
            current_path = os.path.join(current_base, name)
            dirs_to_create.append(current_path)
            accumulated_logs += f"Cloning {current_path}\n"
            if isinstance(children, dict) and children:
                stack.append((current_path, children))
        # base_path, (dir_name, subdirs) = stack.pop()
        # current_path = os.path.join(base_path, dir_name)
        #
        # if not subdirs:  # No subdirectories; it's a leaf
        #     dirs_to_create.append(current_path)
        #     accumulated_logs += f"Cloning {current_path}\n"
        # else:
        #     for subdir in subdirs:  # Add each subdirectory to the stack for further processing
        #         if isinstance(subdir, tuple):
        #             stack.append((current_path, subdir))  # Nested structure
        #         else:  # Direct leaf under the current directory
        #             dirs_to_create.append(os.path.join(current_path, subdir))
        #             accumulated_logs += f"Cloning {os.path.join(current_path, subdir)}\n"
    for dir_to_create in dirs_to_create:
        os.makedirs(dir_to_create, exist_ok=True)
    for loc in LOCAL_MODULE_LOCATIONS:
        sys.path.insert(0, os.path.join(base_app_dir, loc))

    for dirpath, dirnames, filenames in os.walk(install_dir):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            stripped_filename = os.path.relpath(file_path, install_dir)
            alternate_file_location = os.path.join(base_app_dir, stripped_filename)
            if not os.path.exists(alternate_file_location) or INDEV:  # Replace all for indev
                # accumulated_logs += f"{file_path} -> {alternate_file_location}\n"  # To flush config prints in main
                os.makedirs(os.path.dirname(alternate_file_location), exist_ok=True)
                shutil.copyfile(file_path, alternate_file_location)
            # else:
            #     accumulated_logs += f"{alternate_file_location} Already exists\n"  # To flush config prints in main

    os.chdir(base_app_dir)
    return {
        "accumulated_logs": accumulated_logs, "old_cwd": old_cwd, "install_dir": install_dir,
        "base_app_dir": base_app_dir,
    }

@_dc(frozen=True)
class AppInfo:
    """Contains all info on the app"""
    INDEV: bool
    INDEV_KEEP_RUNTIME_FILES: bool
    PROGRAM_NAME: str
    VERSION: int
    VERSION_ADD: str
    OS_LIST: dict[str, dict[str, tuple[str, ...]]]
    PY_LIST: list[tuple[int, int]]
    DIR_STRUCTURE: _DirectoryTree
    LOCAL_MODULE_LOCATIONS: list[str]

def configure(app_info: AppInfo) -> None:
    """Configures all the information into the config module"""
    global INDEV, INDEV_KEEP_RUNTIME_FILES, PROGRAM_NAME, VERSION, VERSION_ADD, PROGRAM_NAME_NORMALIZED, \
        OS_LIST, PY_LIST, DIR_STRUCTURE, LOCAL_MODULE_LOCATIONS
    INDEV = app_info.INDEV
    INDEV_KEEP_RUNTIME_FILES = app_info.INDEV_KEEP_RUNTIME_FILES
    PROGRAM_NAME = app_info.PROGRAM_NAME
    VERSION = app_info.VERSION
    VERSION_ADD = app_info.VERSION_ADD
    PROGRAM_NAME_NORMALIZED = f"{PROGRAM_NAME.lower().replace(' ', '_')}_{VERSION}{VERSION_ADD}"
    OS_LIST = app_info.OS_LIST
    PY_LIST = app_info.PY_LIST
    DIR_STRUCTURE = app_info.DIR_STRUCTURE
    LOCAL_MODULE_LOCATIONS = app_info.LOCAL_MODULE_LOCATIONS

def check() -> RuntimeError | None:
    """Check if environment is suitable"""
    global CHECK_DONE, exit_code, exit_message

    if CHECK_DONE:
        return None
    CHECK_DONE = True

    exit_code, exit_message = 0, "An unknown error occurred"
    platform_versions: dict[str, tuple[str, ...]] | None = OS_LIST.get(platform.system(), None)

    if platform_versions is None:
        exit_code, exit_message = 1, (f"You are currently on {platform.system()}. "
                                      f"Please run this on a supported OS ({', '.join(OS_LIST.keys())}).")

    used_os_major_version: str | None = None
    used_os_minor_version: str | None = None
    for possible_major, possible_minors in platform_versions.items():  # type: ignore
        if platform.release() in possible_major and (platform.version() in possible_minors or possible_minors == ("any",)):
            used_os_minor_version = possible_major
            used_os_major_version = platform.version()
            break
    if used_os_major_version is None or used_os_minor_version is None:
        exit_code, exit_message = 1, (f"You are currently on {platform.release()}{platform.version()}. "
                                      f"Please run this on a supported OS version.")

    if sys.version_info[:2] not in PY_LIST:
        py_versions_strs = [f"{major}.{minor}" for (major, minor) in PY_LIST]
        exit_code, exit_message = 1, (f"You are currently on {'.'.join([str(x) for x in sys.version_info])}. "
                                      f"Please run this using a supported python version ({', '.join(py_versions_strs)}).")
    if exit_code:
        return RuntimeError(exit_message)
    return None

def setup() -> None:
    """Setup the app, this does not include checking for compatibility"""
    # Feed information into globals
    global CONFIG_DONE, exported_logs, base_app_dir, old_cwd
    if CONFIG_DONE or not CHECK_DONE:
        return None
    CONFIG_DONE = True
    exported_vars = _configure()
    exported_logs, base_app_dir, old_cwd = (exported_vars["accumulated_logs"], exported_vars["base_app_dir"],
                                            exported_vars["old_cwd"])
    return None

def do(app_info: AppInfo) -> None:
    """Does the three steps configure, check setup at once."""
    configure(app_info)
    check()
    setup()
