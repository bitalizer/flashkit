"""``flashkit class`` — show details for a single class."""

from __future__ import annotations

import argparse

from ._util import load, bold, dim, cyan, green, yellow


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("class", help="Show class details")
    p.add_argument("file", help="SWF or SWZ file")
    p.add_argument("name", help="Class name (simple or qualified)")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    ws = load(args.file)
    cls = ws.get_class(args.name)

    if cls is None:
        matches = ws.find_classes(name=args.name)
        if len(matches) == 1:
            cls = matches[0]
        elif matches:
            print(f"Ambiguous name '{args.name}', matches:")
            for m in matches:
                print(f"  {m.qualified_name}")
            return
        else:
            print(f"Class '{args.name}' not found.")
            return

    flags = []
    if cls.is_interface:
        flags.append("interface")
    if cls.is_final:
        flags.append("final")
    if cls.is_sealed:
        flags.append("sealed")
    flag_str = f"  [{', '.join(flags)}]" if flags else ""

    print(bold(cls.qualified_name) + dim(flag_str))
    if cls.package:
        print(f"  Package: {cyan(cls.package)}")
    print(f"  Extends: {cyan(cls.super_name)}")
    if cls.interfaces:
        print(f"  Implements: {', '.join(green(i) for i in cls.interfaces)}")

    if cls.fields:
        print(f"\n  {bold('Instance Fields')} ({len(cls.fields)})")
        for f in cls.fields:
            const = "const " if f.is_const else ""
            print(f"    {const}{f.name}: {yellow(f.type_name)}")

    if cls.static_fields:
        print(f"\n  {bold('Static Fields')} ({len(cls.static_fields)})")
        for f in cls.static_fields:
            const = "const " if f.is_const else ""
            print(f"    static {const}{f.name}: {yellow(f.type_name)}")

    if cls.methods:
        print(f"\n  {bold('Instance Methods')} ({len(cls.methods)})")
        for m in cls.methods:
            kind = ""
            if m.is_getter:
                kind = "get "
            elif m.is_setter:
                kind = "set "
            params = ", ".join(
                f"{n}: {t}" if n else t
                for n, t in zip(m.param_names or [""] * len(m.param_types),
                                m.param_types))
            print(f"    {kind}{m.name}({params}): {yellow(m.return_type)}")

    if cls.static_methods:
        print(f"\n  {bold('Static Methods')} ({len(cls.static_methods)})")
        for m in cls.static_methods:
            params = ", ".join(
                f"{n}: {t}" if n else t
                for n, t in zip(m.param_names or [""] * len(m.param_types),
                                m.param_types))
            print(f"    static {m.name}({params}): {yellow(m.return_type)}")
