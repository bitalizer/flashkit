"""
AS3 decompilation — convert AVM2 bytecode back into ActionScript 3 source.

The decompiler consumes a parsed :class:`~flashkit.abc.types.AbcFile` and
produces readable AS3 source at three granularities:

- :func:`decompile_method_body` — just the body of one method.
- :func:`decompile_method` — method signature + body.
- :func:`decompile_class` — full ``package { class { ... } }`` source.

Callers can pass any of: a parsed ``AbcFile``, a :class:`~flashkit.workspace.Workspace`,
or (via :class:`DecompilerCache`) a path to a SWF. Classes can be identified
by index or by name.

The decompiler is a heavy import. It is lazy-loaded via module ``__getattr__``
so ``import flashkit`` stays fast for callers that never decompile anything.

Usage::

    from flashkit import parse_abc
    from flashkit.decompile import decompile_class, decompile_method

    abc = parse_abc(abc_bytes)

    src = decompile_class(abc, name="com.game.Player")
    src = decompile_method(abc, class_index=14, name="update")
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Expose the public symbols to type checkers without triggering the
    # heavy imports at runtime.
    from .method import decompile_method, decompile_method_body
    from .class_ import decompile_class, list_classes
    from .cache import DecompilerCache


__all__ = [
    "decompile_method",
    "decompile_method_body",
    "decompile_class",
    "list_classes",
    "DecompilerCache",
]


def __getattr__(name: str):
    """Lazy-load submodules on first attribute access.

    This keeps ``import flashkit.decompile`` cheap; the actual decompiler
    code (thousands of lines) is only imported when a caller reaches for
    one of the entry points.
    """
    if name in ("decompile_method", "decompile_method_body"):
        from .method import decompile_method, decompile_method_body  # noqa: F401
        return {"decompile_method": decompile_method,
                "decompile_method_body": decompile_method_body}[name]
    if name in ("decompile_class", "list_classes"):
        from .class_ import decompile_class, list_classes  # noqa: F401
        return {"decompile_class": decompile_class,
                "list_classes": list_classes}[name]
    if name == "DecompilerCache":
        from .cache import DecompilerCache
        return DecompilerCache
    raise AttributeError(f"module 'flashkit.decompile' has no attribute {name!r}")
