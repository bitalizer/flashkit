"""Tests for flashkit.decompile.DecompilerCache.

Builds a minimal synthetic SWF on disk, drives the cache through each
public method, and checks that repeated lookups hit the cache (no
re-parse) while an ``mtime`` bump invalidates it.
"""

from __future__ import annotations

import os

import pytest

from flashkit.abc.builder import AbcBuilder
from flashkit.abc.writer import serialize_abc
from flashkit.swf.builder import SwfBuilder
from flashkit.decompile import DecompilerCache, ClassSummary


def _write_swf(tmp_path, class_name: str = "Widget") -> str:
    """Write a minimal SWF with one class ``class_name`` and return
    the absolute path."""
    b = AbcBuilder()
    ns = b.package_namespace(0)
    mn = b.qname(ns, b.string(class_name))
    ctor = b.method()
    b.method_body(
        ctor,
        code=b.asm(b.op_getlocal_0(), b.op_pushscope(), b.op_returnvoid()),
    )
    b.define_class(name=mn, super_name=0, constructor=ctor)
    abc_bytes = serialize_abc(b.build())

    swf = SwfBuilder()
    swf.add_abc("TestAbc", abc_bytes)
    path = tmp_path / "test.swf"
    # uncompressed SWF is simpler for tests — avoids zlib round-trip surprises
    path.write_bytes(swf.build(compress=False))
    return str(path)


def test_list_classes_returns_typed_rows(tmp_path):
    path = _write_swf(tmp_path, "Widget")
    cache = DecompilerCache()

    rows = cache.list_classes(path)
    assert len(rows) == 1
    assert isinstance(rows[0], ClassSummary)
    assert rows[0].name == "Widget"
    # Dict-style access still works for backwards compatibility.
    assert rows[0]["name"] == "Widget"
    assert rows[0].get("full_name") == "Widget"


def test_decompile_class_by_short_name(tmp_path):
    path = _write_swf(tmp_path, "Widget")
    cache = DecompilerCache()

    src = cache.decompile_class(path, "Widget")
    assert "class Widget" in src


def test_decompile_class_missing_raises(tmp_path):
    path = _write_swf(tmp_path, "Widget")
    cache = DecompilerCache()

    with pytest.raises(KeyError):
        cache.decompile_class(path, "NotAClass")


def test_decompile_method_missing_class_raises(tmp_path):
    path = _write_swf(tmp_path, "Widget")
    cache = DecompilerCache()

    with pytest.raises(KeyError):
        cache.decompile_method(path, "NoSuch", "update")


def test_cache_reuses_entry_for_same_mtime(tmp_path):
    path = _write_swf(tmp_path, "Widget")
    cache = DecompilerCache()

    cache.list_classes(path)
    entries_before = dict(cache._entries)

    # Second call must hit the cache — no new entries, same identity.
    cache.list_classes(path)
    assert cache._entries is not entries_before  # same dict, mutated in place
    assert len(cache._entries) == 1
    (key,) = cache._entries
    # Entry tuple should be the literal same object the first call stored.
    assert cache._entries[key] is list(entries_before.values())[0]


def test_cache_invalidates_on_mtime_change(tmp_path):
    path = _write_swf(tmp_path, "Widget")
    cache = DecompilerCache()

    cache.list_classes(path)
    initial_keys = set(cache._entries.keys())
    (initial_key,) = initial_keys
    first_entry = cache._entries[initial_key]

    # Nudge mtime forward. File stats on Windows round to 1s, so
    # a simple ``utime`` two seconds ahead keeps the move detectable.
    new_mtime = os.path.getmtime(path) + 2
    os.utime(path, (new_mtime, new_mtime))

    cache.list_classes(path)
    # Cache key is (abspath, mtime), so the new mtime gets its own slot.
    assert len(cache._entries) == 2
    new_keys = set(cache._entries.keys()) - initial_keys
    (new_key,) = new_keys
    assert cache._entries[new_key] is not first_entry


def test_decompile_class_accepts_pathlike(tmp_path):
    path = _write_swf(tmp_path, "Widget")
    cache = DecompilerCache()

    # Passing a pathlib.Path (not a str) must work.
    from pathlib import Path
    src = cache.decompile_class(Path(path), "Widget")
    assert "class Widget" in src
