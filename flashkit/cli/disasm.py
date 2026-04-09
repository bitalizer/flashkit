"""``flashkit disasm`` — disassemble method bytecode."""

from __future__ import annotations

import argparse

from ._util import load, bold


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("disasm", help="Disassemble method bytecode")
    p.add_argument("file", help="SWF or SWZ file")
    p.add_argument("--class", dest="class_name",
                   help="Class to disassemble")
    p.add_argument("--method-index", type=int,
                   help="Method index to disassemble")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    ws = load(args.file)

    from ..abc.disasm import decode_instructions

    if args.method_index is not None:
        for abc in ws.abc_blocks:
            for mb in abc.method_bodies:
                if mb.method == args.method_index:
                    print(bold(f"Method {mb.method}") +
                          f"  (max_stack={mb.max_stack}, "
                          f"locals={mb.local_count}, "
                          f"code={len(mb.code)} bytes)")
                    for instr in decode_instructions(mb.code):
                        ops = ", ".join(str(o) for o in instr.operands)
                        print(f"  0x{instr.offset:04X}  "
                              f"{instr.mnemonic:<24s} {ops}")
                    return
        print(f"Method index {args.method_index} not found.")
        return

    if args.class_name:
        cls = ws.get_class(args.class_name)
        if cls is None:
            matches = ws.find_classes(name=args.class_name)
            if len(matches) == 1:
                cls = matches[0]
            else:
                print(f"Class '{args.class_name}' not found.")
                return

        for abc in ws.abc_blocks:
            method_indices = set()
            for m in cls.all_methods:
                method_indices.add(m.method_index)
            method_indices.add(cls.constructor_index)

            for mb in abc.method_bodies:
                if mb.method in method_indices:
                    mname = f"method_{mb.method}"
                    if mb.method == cls.constructor_index:
                        mname = f"{cls.name}()"
                    else:
                        for m in cls.all_methods:
                            if m.method_index == mb.method:
                                mname = m.name
                                break

                    print(bold(f"{cls.name}.{mname}") +
                          f"  ({len(mb.code)} bytes)")
                    for instr in decode_instructions(mb.code):
                        ops = ", ".join(str(o) for o in instr.operands)
                        print(f"  0x{instr.offset:04X}  "
                              f"{instr.mnemonic:<24s} {ops}")
                    print()
        return

    print("Specify --class or --method-index.")
