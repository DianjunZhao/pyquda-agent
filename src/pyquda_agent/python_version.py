"""Shared Python-version policy for CLI and validation scripts."""

from __future__ import annotations

import sys


MIN_PYTHON = (3, 10)


def supported_python_version_string() -> str:
    return ".".join(str(part) for part in MIN_PYTHON)


def python_version_ok(version_info: tuple[int, ...] | None = None) -> bool:
    current = version_info or sys.version_info
    return tuple(current[:2]) >= MIN_PYTHON


def unsupported_python_message(*, context: str) -> str:
    current = ".".join(str(part) for part in sys.version_info[:3])
    required = supported_python_version_string()
    return (
        f"{context} requires Python >= {required}. Current interpreter: {current} ({sys.executable}). "
        "Re-run with an explicit >=3.10 interpreter, for example a virtualenv/conda/pyenv Python path; "
        "do not assume bare `python3` is new enough on every machine."
    )


def ensure_supported_python(*, context: str) -> None:
    if python_version_ok():
        return
    raise SystemExit(unsupported_python_message(context=context))
