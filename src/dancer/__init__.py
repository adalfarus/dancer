"""Dancer"""
from . import io, cli, concurrency, data, security, system, timing, web
from ._app import *
from ._default_apps import *
from ._default_modules import *
from .config import do as _do
from .system import diagnose_shutdown_blockers

import typing as _ty
import types as _ts

__version__ = "0.0.1.0b0"

from dataclasses import dataclass as _dc
_DirectoryTree = dict[str, _ty.Union["_DirectoryTree", None]]
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
    WORKING_OS_LIST: dict[str, dict[str, tuple[str, ...]]]
    UNTESTED_OS_LIST: dict[str, dict[str, tuple[str, ...]]]
    INCOMPATIBLE_OS_LIST: dict[str, dict[str, tuple[str, ...]]]
    PY_LIST: list[tuple[int, int]]
    DIR_STRUCTURE: _DirectoryTree
    LOCAL_MODULE_LOCATIONS: list[str]


app_config: AppConfig | None = None
_globs: dict[str, _ty.Any] = {}


def make_global(key: str, value: _ty.Any) -> None:
    global _globs
    _globs[key] = value

def get_global(key: str) -> _ty.Any | None:
    return _globs.get(key)

def configure(configuration: AppConfig):
    ...

def late_init_package(pkg: str, app_info: AppConfig) -> _ts.ModuleType:
    _do(app_info)
    pkg = __import__(pkg, globals(), locals(), [pkg])
    start(pkg.App, pkg.parser, pkg.exit_codes)
    return pkg

def package(pkg_name: str) -> str:
    pkg: _ts.ModuleType = __import__(pkg_name, globals(), locals(), [pkg_name])
    _do(app_info=pkg.app_info)
    pkg_app: _ts.ModuleType = __import__(f"{pkg_name}.app", globals(), locals(), [pkg_name])
    start(pkg_app.App, pkg.parser, pkg_app.exit_codes)
    results: str = diagnose_shutdown_blockers(return_result=True)
    return results
