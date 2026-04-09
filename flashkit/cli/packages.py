"""``flashkit packages`` — list packages and their class counts."""

from __future__ import annotations

import argparse

from ._util import load, bold, dim


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("packages", help="List packages")
    p.add_argument("file", help="SWF or SWZ file")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    ws = load(args.file)
    pkgs = ws.packages

    if not pkgs:
        print("No packages found.")
        return

    print(bold(f"{'Package':<50} {'Classes':>8}"))
    print("-" * 60)
    for p in sorted(pkgs, key=lambda p: p.name):
        name = p.name or dim("(default)")
        print(f"{name:<50} {len(p.classes):>8}")

    print(f"\n{len(pkgs)} package(s)")
