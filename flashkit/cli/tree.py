"""``flashkit tree`` — show inheritance tree for a class."""

from __future__ import annotations

import argparse

from ._util import load, bold, green


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("tree", help="Show inheritance tree")
    p.add_argument("file", help="SWF or SWZ file")
    p.add_argument("name", help="Class name")
    p.add_argument("-a", "--ancestors", action="store_true",
                   help="Show ancestors instead of descendants")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    ws = load(args.file)

    from ..analysis.inheritance import InheritanceGraph
    graph = InheritanceGraph.from_classes(ws.classes)

    name = args.name

    if args.ancestors:
        chain = graph.get_all_parents(name)
        if not chain:
            print(f"No ancestors for '{name}' (root or not found).")
            return
        print(bold(f"Ancestors of {name}:"))
        for i, c in enumerate(chain):
            print(f"  {'  ' * i}{c}")
        print(f"  {'  ' * len(chain)}{green(name)}")
        return

    children = graph.get_all_children(name)
    direct = graph.get_children(name)

    if not children and not direct:
        print(f"No subclasses of '{name}'.")
        return

    def _print_tree(n: str, depth: int = 0) -> None:
        prefix = "  " * depth
        print(f"{prefix}{green(n) if depth == 0 else n}")
        for child in sorted(graph.get_children(n)):
            _print_tree(child, depth + 1)

    _print_tree(name)
    print(f"\n{len(children)} descendant(s)")
