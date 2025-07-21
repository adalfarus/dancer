"""Dancer"""
from . import config, io, cli, concurrency, data, security, system, timing, web
from ._app import *
from ._default_apps import *
from ._default_modules import *

import typing as _ty

__version__ = "0.0.0.1a8"


_globs: dict[str, _ty.Any] = {}


def make_global(key: str, value: _ty.Any) -> None:
    global _globs
    _globs[key] = value

def get_global(key: str) -> _ty.Any | None:
    return _globs.get(key)
