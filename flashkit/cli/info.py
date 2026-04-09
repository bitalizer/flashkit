"""``flashkit info`` — show high-level file summary."""

from __future__ import annotations

import argparse

from ._util import load, bold


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("info", help="Show file summary")
    p.add_argument("file", help="SWF or SWZ file")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    ws = load(args.file)
    res = ws.resources[0]

    print(bold(f"File: {res.path}"))
    print(f"  Format:     {res.kind.upper()}")
    if res.swf_version is not None:
        print(f"  SWF version: {res.swf_version}")
    if res.swf_tags is not None:
        print(f"  Tags:       {len(res.swf_tags)}")
    print(f"  ABC blocks: {len(res.abc_blocks)}")
    print(f"  Classes:    {res.class_count}")
    print(f"  Methods:    {res.method_count}")
    print(f"  Strings:    {res.string_count}")

    if res.abc_blocks:
        abc = res.abc_blocks[0]
        print(f"  Namespaces: {len(abc.namespace_pool)}")
        print(f"  Multinames: {len(abc.multiname_pool)}")
        interfaces = sum(1 for c in ws.classes if c.is_interface)
        if interfaces:
            print(f"  Interfaces: {interfaces}")

    pkgs = ws.packages
    if pkgs:
        print(f"  Packages:   {len(pkgs)}")
