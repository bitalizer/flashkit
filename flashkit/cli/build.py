"""``flashkit build`` — rebuild a SWF (recompress or decompress)."""

from __future__ import annotations

import argparse
from pathlib import Path

from ._util import load


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("build", help="Rebuild SWF (recompress/decompress)")
    p.add_argument("file", help="SWF file")
    p.add_argument("-o", "--output", help="Output file path")
    p.add_argument("-d", "--decompress", action="store_true",
                   help="Output uncompressed FWS")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    ws = load(args.file)
    res = ws.resources[0]

    if res.swf_tags is None:
        print("Cannot rebuild: not a SWF file.")
        return

    from ..swf.builder import rebuild_swf

    compress = not args.decompress
    output = rebuild_swf(res.swf_header, res.swf_tags, compress=compress)

    out_path = args.output or args.file
    Path(out_path).write_bytes(output)
    mode = "compressed" if compress else "uncompressed"
    print(f"Wrote {out_path} ({len(output)} bytes, {mode})")
