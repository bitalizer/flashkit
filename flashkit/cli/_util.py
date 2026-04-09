"""Shared CLI utilities — ANSI colors and workspace loading."""

from __future__ import annotations

import os
import sys

from ..workspace import Workspace

# Respect NO_COLOR convention (https://no-color.org/) and non-TTY output.
_NO_COLOR = not sys.stdout.isatty() or os.environ.get("NO_COLOR", "") != ""


def _c(code: str, text: str) -> str:
    if _NO_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


def bold(t: str) -> str:
    return _c("1", t)


def dim(t: str) -> str:
    return _c("2", t)


def green(t: str) -> str:
    return _c("32", t)


def cyan(t: str) -> str:
    return _c("36", t)


def yellow(t: str) -> str:
    return _c("33", t)


def red(t: str) -> str:
    return _c("31", t)


def magenta(t: str) -> str:
    return _c("35", t)


def load(path: str) -> Workspace:
    """Load a SWF/SWZ file into a Workspace."""
    ws = Workspace()
    ws.load(path)
    return ws
