"""Configures your environment"""
import enum
import warnings
from dataclasses import dataclass as _dc
import platform
import shutil
import sys
import os
import re

import typing as _ty
import types as _ts
import typing_extensions as _tx

@_dc(frozen=True)
class OSEntry:
    """Contains all info on the OS"""
    major_version: str
    minor_versions: tuple[str, ...]
    machines: tuple[str, ...]

_DirectoryTree = dict[str, _ty.Union["_DirectoryTree", None]]
PlatformVersionsType = dict[str, tuple[tuple[str, ...], tuple[str, ...]]]
OSListType = dict[str, list[OSEntry]]  # dict[str, PlatformVersionsType]

INDEV: bool
INDEV_KEEP_RUNTIME_FILES: bool
COMPILE_TIME_FLAGS: bool
PROGRAM_NAME: str
VERSION: int
VERSION_ADD: str
PROGRAM_NAME_NORMALIZED: str
WORKING_OS_LIST: OSListType
UNTESTED_OS_LIST: OSListType
INCOMPATIBLE_OS_LIST: OSListType
PY_LIST: list[tuple[int, int]]
DIR_STRUCTURE: _DirectoryTree
LOCAL_MODULE_LOCATIONS: list[str]

RUNTIME_FILE_EXTENSIONS: tuple[str, ...] = (
    ".json",
    ".yml", ".yaml",
    ".ini",
    ".toml",
    ".conf",
    ".cfg",
    ".xml",
    ".log",
    ".err",
    ".out",
    ".trace",
    ".dmp",
    ".db",
    ".sqlite", ".sqlite3",
    ".dat",
    ".bak",
    ".tmp",
    ".cache",
    ".mo", ".po",
    ".lang",
    ".key", ".pem",
    ".cred", ".auth",
    ".unicode",
    ".map",
    ".layout",
    ".mod",
    ".profile",
    ".session"
)

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
    """Returns VERSION + VERSION_ADD as a string"""
    return str(VERSION) + VERSION_ADD

# From aplustools.io.env
def _get_appdata_dir(app_dir: str, scope: _ty.Literal["user", "global"] = "global"):
    system = platform.system()
    if system == "Windows":
        if scope == "user":
            return os.path.join(
                os.environ.get("APPDATA"), app_dir
            )  # App data for the current user
        return os.path.join(
            os.environ.get("PROGRAMDATA"), app_dir
        )  # App data for all users
    elif system == "Darwin":
        if scope == "user":
            return os.path.join(
                os.path.expanduser("~"), "Library", "Application Support", app_dir
            )  # App data for the current user
        return os.path.join(
            "/Library/Application Support", app_dir
        )  # App data for all users
    elif system == "Linux":
        if scope == "user":
            return os.path.join(
                os.path.expanduser("~"), ".local", "share", app_dir
            )  # App data for the current user
        return os.path.join("/usr/local/share", app_dir)  # App data for all users
    elif system == "FreeBSD":
        if scope == "user":
            return os.path.join(os.path.expanduser("~"), ".local", "share", app_dir)
        return os.path.join("/usr/local/share", app_dir)

def _configure() -> dict[str, str]:
    if is_compiled():
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        if not sys.stdout:
            sys.stdout = open(os.devnull, "w")
        if not sys.stderr:
            sys.stderr = open(os.devnull, "w")

    if COMPILE_TIME_FLAGS:
        import multiprocessing
        multiprocessing.freeze_support()

    accumulated_logs = "Starting cloning of defaults ...\n"
    old_cwd = os.getcwd()
    install_dir = os.path.join(old_cwd, "default-config")
    # So we never have a relative dir, even if something fails
    base_app_dir = os.path.abspath(_get_appdata_dir(f"{PROGRAM_NAME_NORMALIZED}_{VERSION}{VERSION_ADD}", "user"))

    if INDEV and os.path.exists(base_app_dir):  # Remove everything to simulate a fresh install
        if not INDEV_KEEP_RUNTIME_FILES:
            shutil.rmtree(base_app_dir)
            os.mkdir(base_app_dir)
        else:  # Skip only .db or .log files
            for root, dirs, files in os.walk(base_app_dir, topdown=False):
                for file in files:
                    if not file.endswith(RUNTIME_FILE_EXTENSIONS):
                        os.remove(os.path.join(root, file))
                for directory in dirs:
                    dir_path = os.path.join(root, directory)
                    if not any(f.endswith(RUNTIME_FILE_EXTENSIONS) or os.path.isdir(os.path.join(dir_path, f)) for f in os.listdir(dir_path)):
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
class AppConfig:
    """Contains all info on the app"""
    INDEV: bool
    INDEV_KEEP_RUNTIME_FILES: bool
    COMPILE_TIME_FLAGS: bool
    PROGRAM_NAME: str
    PROGRAM_NAME_NORMALIZED: str
    VERSION: int
    VERSION_ADD: str
    WORKING_OS_LIST: OSListType
    UNTESTED_OS_LIST: OSListType
    INCOMPATIBLE_OS_LIST: OSListType
    PY_LIST: list[tuple[int, int]]
    DIR_STRUCTURE: _DirectoryTree
    LOCAL_MODULE_LOCATIONS: list[str]

def configure(app_config: AppConfig) -> None:
    """Configures all the information into the config module"""
    global INDEV, INDEV_KEEP_RUNTIME_FILES, COMPILE_TIME_FLAGS, PROGRAM_NAME, VERSION, VERSION_ADD, \
        PROGRAM_NAME_NORMALIZED,  WORKING_OS_LIST, UNTESTED_OS_LIST, INCOMPATIBLE_OS_LIST, PY_LIST, DIR_STRUCTURE, \
        LOCAL_MODULE_LOCATIONS
    INDEV = app_config.INDEV
    INDEV_KEEP_RUNTIME_FILES = app_config.INDEV_KEEP_RUNTIME_FILES
    COMPILE_TIME_FLAGS = app_config.COMPILE_TIME_FLAGS
    PROGRAM_NAME = app_config.PROGRAM_NAME
    VERSION = app_config.VERSION
    VERSION_ADD = app_config.VERSION_ADD
    PROGRAM_NAME_NORMALIZED = app_config.PROGRAM_NAME_NORMALIZED
    WORKING_OS_LIST = app_config.WORKING_OS_LIST
    UNTESTED_OS_LIST = app_config.UNTESTED_OS_LIST
    INCOMPATIBLE_OS_LIST = app_config.INCOMPATIBLE_OS_LIST
    PY_LIST = app_config.PY_LIST
    DIR_STRUCTURE = app_config.DIR_STRUCTURE
    LOCAL_MODULE_LOCATIONS = app_config.LOCAL_MODULE_LOCATIONS

class OSListExitState(enum.Enum):
    SystemNotSupported = 0
    ReleaseNotSupported = 1
    VersionNotSupported = 2
    ReleaseOrVersionNotSupported = 3
    Supported = 4

#T = _ty.TypeVar("T")
#def get_from_os_list(os_list: OSListType, key: str, base: T = None) -> OSEntry | T:
#    for osl in os_list:
#        if osl.os_name == key:
#            return osl
#    return base

def _check_os_list(system: str, release: str, version: str, machine: str, os_list: OSListType) -> tuple[OSListExitState, str, str, str]:
    platform_versions: list[OSEntry] | None = os_list.get(system, None)

    if platform_versions is None:
        return OSListExitState.SystemNotSupported, "", "", ""

    for ose in platform_versions:
        possible_major, (possible_minors, possible_machines) = ose.major_version, (ose.minor_versions, ose.machines)
        if re.fullmatch(possible_major, release):
            minor_matches = [re.fullmatch(possible_minor, version) is not None for possible_minor in
                       possible_minors]

            if any(minor_matches) or possible_minors == ("any",):
                machine_matches = [re.fullmatch(possible_machine, machine) is not None for possible_machine in
                           possible_machines]

                if any(machine_matches) or possible_machines == ("any",):
                    return OSListExitState.Supported, release, version, machine  # Currently, this is redundant, maybe not in the future

    return OSListExitState.ReleaseOrVersionNotSupported, "", "", ""

def _format_os_list(os_list: OSListType) -> str:
    return ", ".join(os_list.keys())

def check() -> RuntimeError | UserWarning | str:
    """Check if environment is suitable"""
    global CHECK_DONE, exit_code, exit_message

    if CHECK_DONE:
        return "None"
    CHECK_DONE = True

    exit_code, exit_message = 1, "An unknown error occurred"

    #! Add .machine()
    system, release, version, machine = platform.system(), platform.release(), platform.version(), platform.machine()
    full_config = f"{system} {release} {version} ({machine})"

    # Check for incompatible configuration first
    incompatible_state, _, _, _ = _check_os_list(system, release, version, machine, INCOMPATIBLE_OS_LIST)
    # Check for untested but supported configuration
    untested_state, _, _, _ = _check_os_list(system, release, version, machine, UNTESTED_OS_LIST)
    working_state, _, _, _ = _check_os_list(system, release, version, machine, WORKING_OS_LIST)
    if incompatible_state == OSListExitState.Supported:
        exit_code = 1  # Exit code 1 means an error
        exit_message = (
            f"Your current configuration ({full_config}) is incompatible with this program, please try with a "
            f"configuration that is supported ({_format_os_list(UNTESTED_OS_LIST)} / "
            f"{_format_os_list(WORKING_OS_LIST)})"
        )
    elif working_state == OSListExitState.SystemNotSupported:
        exit_code = 1
        exit_message = (
            f"You are currently on {platform.system()}. Please run this on a supported OS "
            f"({', '.join(WORKING_OS_LIST.keys())})."
        )
    elif working_state == OSListExitState.ReleaseOrVersionNotSupported:
        exit_code = 1
        exit_message = (
            f"You are currently on {full_config}. Use a supported release/version for {system} "
            f"({WORKING_OS_LIST[system]})."
        )
    elif working_state == OSListExitState.Supported:
        exit_code = 0
        exit_message = f"{full_config} with Python {sys.version_info[0]}.{sys.version_info[1]} is fully supported."
    elif untested_state == OSListExitState.Supported:
        exit_code = 2  # Exit Code 2 means a warning
        exit_message = (
            f"Your current configuration ({full_config}) is supported by this program, but untested. Consider using a "
            f"tested configuration ({_format_os_list(WORKING_OS_LIST)})"
        )

    if sys.version_info[:2] not in PY_LIST:
        py_versions_strs = [f"{major}.{minor}" for (major, minor) in PY_LIST]
        exit_code, exit_message = 1, (f"You are currently on {'.'.join([str(x) for x in sys.version_info])}. "
                                      f"Please run this using a supported python version ({', '.join(py_versions_strs)}).")

    if exit_code == 1:
        return RuntimeError(exit_message)
    elif exit_code == 2:
        return UserWarning(exit_message)
    return exit_message

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

def do(app_info: AppConfig) -> None:
    """Does the three steps configure, check setup at once."""
    configure(app_info)
    err = check()
    if isinstance(err, RuntimeError):
        raise err
    elif isinstance(err, UserWarning):
        warnings.warn(
            str(err),
            type(err),
            stacklevel=2
        )
    else:
        print(err)
    setup()
