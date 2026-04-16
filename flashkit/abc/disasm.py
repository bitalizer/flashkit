"""
AVM2 bytecode disassembler / instruction decoder.

Walks the raw bytecode in ``MethodBodyInfo.code`` and yields structured
``Instruction`` objects. This is the foundation for call graph analysis,
cross-reference indexing, and string constant discovery.

Usage::

    from flashkit.abc.disasm import decode_instructions

    for instr in decode_instructions(method_body.code):
        print(f"0x{instr.offset:04X}  {instr.mnemonic}  {instr.operands}")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from ..errors import ABCParseError
from .parser import read_u30, read_u8
from .opcodes import (
    OPCODE_TABLE,
    OP_LOOKUPSWITCH, OP_DEBUG,
    OP_GETPROPERTY, OP_SETPROPERTY, OP_INITPROPERTY,
    OP_GETLEX, OP_FINDPROPSTRICT, OP_FINDPROPERTY,
    OP_CALLPROPERTY, OP_CALLPROPVOID, OP_CALLPROPLEX,
    OP_CALLSUPER, OP_CALLSUPERVOID,
    OP_CONSTRUCTPROP,
    OP_GETSUPER, OP_SETSUPER,
    OP_GETDESCENDANTS, OP_DELETEPROPERTY,
    OP_COERCE, OP_ASTYPE, OP_ISTYPE,
    OP_PUSHSTRING, OP_PUSHINT, OP_PUSHUINT, OP_PUSHDOUBLE,
    OP_NEWCLASS,
)

log = logging.getLogger(__name__)


@dataclass(slots=True)
class Instruction:
    """A single decoded AVM2 instruction.

    Attributes:
        offset: Byte offset of this instruction in the method body code.
        opcode: Opcode byte value.
        mnemonic: Human-readable opcode name.
        operands: List of decoded operand values.
        size: Total size in bytes (opcode + operands).
    """
    offset: int
    opcode: int
    mnemonic: str
    operands: list[int] = field(default_factory=list)
    size: int = 1


@dataclass(slots=True)
class ResolvedInstruction:
    """An AVM2 instruction with operands resolved to readable names.

    Created by ``resolve_instructions()`` from raw ``Instruction`` objects.
    Multiname indices become class/field/method names, string indices become
    quoted literals, int/uint/double indices become numeric values.

    Attributes:
        offset: Byte offset in the method body.
        mnemonic: Opcode name (e.g. ``"getproperty"``).
        operands: Human-readable operand strings.
    """
    offset: int
    mnemonic: str
    operands: list[str] = field(default_factory=list)


# The authoritative opcode table lives in :mod:`flashkit.abc.opcodes`.
# ``_LOOKUP`` is a direct alias so downstream code that imported it keeps
# working; new code should import ``OPCODE_TABLE`` from :mod:`.opcodes`.

_LOOKUP = OPCODE_TABLE


def _read_s24(data: bytes, offset: int) -> tuple[int, int]:
    """Read a signed 24-bit integer (little-endian)."""
    val = data[offset] | (data[offset + 1] << 8) | (data[offset + 2] << 16)
    if val & 0x800000:
        val -= 0x1000000
    return val, offset + 3


# ── Fast operand-format table for the lightweight scanner ──────────────────
# Maps every known opcode to an integer encoding its operand format:
#   0 = none, 1 = u8, 2 = u30, 3 = u30u30, 4 = s24, 5 = lookupswitch, 6 = debug
_FMT_CODE = {"": 0, "u8": 1, "u30": 2, "u30u30": 3, "s24": 4, "u30u8": 3}

def _build_skip_table() -> list[int]:
    """Build a 256-entry table: opcode → operand format code.

    Unknown opcodes get format code 0xFF (sentinel for "stop scanning").
    """
    tbl = [0xFF] * 256
    for op, (_, fmt) in _LOOKUP.items():
        if fmt == "special":
            # OP_LOOKUPSWITCH=5, OP_DEBUG=6
            tbl[op] = 5 if op == OP_LOOKUPSWITCH else 6
        else:
            tbl[op] = _FMT_CODE.get(fmt, 0)
    return tbl

_SKIP_TABLE = _build_skip_table()


def _skip_u30(data: bytes, off: int) -> int:
    """Advance past a u30 without decoding its value."""
    for _ in range(5):
        if (data[off] & 0x80) == 0:
            return off + 1
        off += 1
    return off


def scan_relevant_opcodes(
    code: bytes,
    opcodes: frozenset[int],
) -> list[tuple[int, int, int]]:
    """Lightweight bytecode scanner that only decodes opcodes of interest.

    Walks the bytecode stream, skipping operands for irrelevant opcodes
    via a precomputed table lookup. For opcodes in *opcodes*, decodes
    the first u30 operand and records the hit.

    This avoids creating Instruction objects, mnemonic strings, and
    operand lists for the vast majority of instructions.

    Args:
        code: Raw bytecode bytes (from MethodBodyInfo.code).
        opcodes: Set of opcode values to capture.

    Returns:
        List of ``(offset, opcode, first_operand)`` tuples for matched
        instructions. The first operand is always the first u30 in the
        instruction's operand stream (valid for u30 and u30u30 formats).
    """
    results: list[tuple[int, int, int]] = []
    off = 0
    code_len = len(code)
    skip_table = _SKIP_TABLE

    while off < code_len:
        start = off
        op = code[off]
        off += 1
        fmt = skip_table[op]

        if op in opcodes:
            # All relevant opcodes have u30 or u30u30 format — decode first u30
            try:
                val, off = read_u30(code, off)
            except (IndexError, ValueError):
                break
            results.append((start, op, val))
            # If u30u30, skip the second u30
            if fmt == 3:
                try:
                    off = _skip_u30(code, off)
                except IndexError:
                    break
            continue

        # Skip operands for irrelevant opcodes
        try:
            if fmt == 0:       # no operands
                pass
            elif fmt == 1:     # u8
                off += 1
            elif fmt == 2:     # u30
                off = _skip_u30(code, off)
            elif fmt == 3:     # u30u30
                off = _skip_u30(code, off)
                off = _skip_u30(code, off)
            elif fmt == 4:     # s24
                off += 3
            elif fmt == 5:     # lookupswitch
                off += 3  # default s24
                case_count, off = read_u30(code, off)
                off += (case_count + 1) * 3  # case s24s
            elif fmt == 6:     # debug
                off += 1  # debug_type u8
                off = _skip_u30(code, off)  # index u30
                off += 1  # reg u8
                off = _skip_u30(code, off)  # extra u30
            else:
                # Unknown opcode — can't determine size, bail out
                break
        except (IndexError, ValueError):
            break

    return results


def decode_instructions(code: bytes,
                        strict: bool = False) -> list[Instruction]:
    """Decode an AVM2 bytecode stream into a list of instructions.

    Args:
        code: Raw bytecode bytes (from MethodBodyInfo.code).
        strict: If True, raise ``ABCParseError`` on any decode problem
                (unknown opcodes, truncated operands). If False (default),
                log warnings and emit partial instructions.

    Returns:
        List of decoded Instruction objects.

    Raises:
        ABCParseError: Only when ``strict=True`` and a problem is found.
    """
    instructions: list[Instruction] = []
    off = 0
    code_len = len(code)

    while off < code_len:
        start = off
        op = code[off]
        off += 1

        entry = _LOOKUP.get(op)
        if entry is None:
            msg = f"Unknown opcode 0x{op:02X} at offset 0x{start:04X}"
            if strict:
                raise ABCParseError(msg)
            log.warning(msg)
            instructions.append(Instruction(
                offset=start, opcode=op, mnemonic=f"unknown_0x{op:02X}",
                operands=[], size=1))
            continue

        mnemonic, fmt = entry
        operands: list[int] = []

        try:
            if fmt == "":
                pass
            elif fmt == "u8":
                val, off = read_u8(code, off)
                operands.append(val)
            elif fmt == "u30":
                val, off = read_u30(code, off)
                operands.append(val)
            elif fmt == "u30u30":
                val1, off = read_u30(code, off)
                val2, off = read_u30(code, off)
                operands.extend([val1, val2])
            elif fmt == "s24":
                val, off = _read_s24(code, off)
                operands.append(val)
            elif fmt == "special":
                if op == OP_LOOKUPSWITCH:
                    default_off, off = _read_s24(code, off)
                    case_count, off = read_u30(code, off)
                    operands.append(default_off)
                    operands.append(case_count)
                    for _ in range(case_count + 1):
                        case_off, off = _read_s24(code, off)
                        operands.append(case_off)
                elif op == OP_DEBUG:
                    debug_type, off = read_u8(code, off)
                    index, off = read_u30(code, off)
                    reg, off = read_u8(code, off)
                    extra, off = read_u30(code, off)
                    operands.extend([debug_type, index, reg, extra])
        except (IndexError, ValueError) as e:
            msg = (f"Truncated operand for {mnemonic} at offset "
                   f"0x{start:04X}: {e}")
            if strict:
                raise ABCParseError(msg) from e
            log.warning(msg)
            # Emit what we have so far and stop decoding
            instructions.append(Instruction(
                offset=start, opcode=op, mnemonic=mnemonic,
                operands=operands, size=off - start))
            break

        instructions.append(Instruction(
            offset=start, opcode=op, mnemonic=mnemonic,
            operands=operands, size=off - start))

    return instructions


# ── Opcodes grouped by operand resolution type ─────────────────────────────
# First operand is a multiname pool index
_MULTINAME_FIRST = frozenset({
    OP_GETPROPERTY, OP_SETPROPERTY, OP_INITPROPERTY,
    OP_GETLEX, OP_FINDPROPSTRICT, OP_FINDPROPERTY,
    OP_CALLPROPERTY, OP_CALLPROPVOID, OP_CONSTRUCTPROP,
    OP_CALLPROPLEX, OP_CALLSUPER, OP_CALLSUPERVOID,
    OP_GETSUPER, OP_SETSUPER,
    OP_GETDESCENDANTS, OP_DELETEPROPERTY,
    OP_COERCE, OP_ASTYPE, OP_ISTYPE,
})

# First operand is a string pool index
_STRING_FIRST = frozenset({OP_PUSHSTRING})

# First operand is an int pool index
_INT_FIRST = frozenset({OP_PUSHINT})

# First operand is a uint pool index
_UINT_FIRST = frozenset({OP_PUSHUINT})

# First operand is a double pool index
_DOUBLE_FIRST = frozenset({OP_PUSHDOUBLE})


def resolve_instructions(
    abc: "AbcFile",
    instructions: list[Instruction],
) -> list[ResolvedInstruction]:
    """Resolve raw instruction operands to human-readable strings.

    Multiname indices become names, string indices become quoted strings,
    int/uint/double indices become literal values. Everything else stays
    as raw numbers.

    Args:
        abc: The AbcFile for constant pool lookups.
        instructions: Raw decoded instructions.

    Returns:
        List of ResolvedInstruction with string operands.
    """
    from .types import AbcFile as _AbcFile  # noqa: F811
    from ..info.member_info import resolve_multiname

    resolved = []
    for instr in instructions:
        ops: list[str] = []
        op = instr.opcode

        for i, val in enumerate(instr.operands):
            if i == 0 and op in _MULTINAME_FIRST:
                try:
                    ops.append(resolve_multiname(abc, val))
                except (IndexError, KeyError):
                    ops.append(f"multiname[{val}]")
            elif i == 0 and op in _STRING_FIRST:
                if 0 < val < len(abc.string_pool):
                    ops.append(f'"{abc.string_pool[val]}"')
                else:
                    ops.append(f"string[{val}]")
            elif i == 0 and op in _INT_FIRST:
                if 0 < val < len(abc.int_pool):
                    ops.append(str(abc.int_pool[val]))
                else:
                    ops.append(f"int[{val}]")
            elif i == 0 and op in _UINT_FIRST:
                if 0 < val < len(abc.uint_pool):
                    ops.append(str(abc.uint_pool[val]))
                else:
                    ops.append(f"uint[{val}]")
            elif i == 0 and op in _DOUBLE_FIRST:
                if 0 < val < len(abc.double_pool):
                    ops.append(str(abc.double_pool[val]))
                else:
                    ops.append(f"double[{val}]")
            elif i == 0 and op == OP_NEWCLASS:
                # val = class index
                if 0 <= val < len(abc.instances):
                    try:
                        ops.append(resolve_multiname(abc, abc.instances[val].name))
                    except (IndexError, KeyError):
                        ops.append(f"class[{val}]")
                else:
                    ops.append(f"class[{val}]")
            else:
                ops.append(str(val))

        resolved.append(ResolvedInstruction(
            offset=instr.offset,
            mnemonic=instr.mnemonic,
            operands=ops,
        ))

    return resolved
