# flashkit

Parse, analyze, and manipulate Adobe Flash SWF files and AVM2 bytecode.

## Install

```bash
pip install -e .
```

## Quick start

```bash
flashkit info application.swf          # file summary
flashkit classes application.swf       # list all classes
flashkit class application.swf Player  # inspect a class
flashkit strings application.swf -s config  # search strings
```

```python
from flashkit.workspace import Workspace

ws = Workspace()
ws.load_swf("application.swf")
for cls in ws.classes:
    print(cls.qualified_name, cls.super_name)
```

---

## CLI reference

```
flashkit <command> <file> [options]
```

| Command | Description |
|---------|-------------|
| `info` | File summary (format, version, class/method/string counts) |
| `tags` | List all SWF tags with types and sizes |
| `classes` | List classes with optional filters |
| `class` | Inspect a single class (fields, methods, inheritance) |
| `strings` | List or search string constants |
| `disasm` | Disassemble AVM2 bytecode |
| `callers` | Find callers of a method or property |
| `callees` | Find outgoing calls from a method |
| `refs` | Find cross-references to a name |
| `tree` | Show inheritance tree (descendants or ancestors) |
| `packages` | List packages and class counts |
| `extract` | Extract raw ABC blocks to files |
| `build` | Rebuild SWF (recompress or decompress) |

<details>
<summary><strong>flashkit info</strong> — file summary</summary>

```
$ flashkit info application.swf
File: application.swf
  Format:     SWF
  SWF version: 40
  Tags:       142
  ABC blocks: 1
  Classes:    823
  Methods:    14210
  Strings:    35482
  Packages:   47
```

</details>

<details>
<summary><strong>flashkit tags</strong> — list SWF tags</summary>

```
$ flashkit tags application.swf
#      Type     Name                                      Size
--------------------------------------------------------------
0      69       FileAttributes                               4
1      9        SetBackgroundColor                           3
2      82       DoABC2                                 1847293
3      76       SymbolClass                                 14
4      0        End                                          0

5 tags total
```

</details>

<details>
<summary><strong>flashkit classes</strong> — list classes</summary>

```bash
flashkit classes application.swf                    # all classes
flashkit classes application.swf -p com.game        # filter by package
flashkit classes application.swf -e Sprite          # filter by superclass
flashkit classes application.swf -s Manager         # search by name
flashkit classes application.swf -i                 # interfaces only
flashkit classes application.swf -v                 # verbose output
```

</details>

<details>
<summary><strong>flashkit class</strong> — inspect a single class</summary>

```
$ flashkit class application.swf PlayerManager
PlayerManager
  Package: com.game
  Extends: EventDispatcher
  Implements: IDisposable, ITickable

  Instance Fields (3)
    mHealth: Number
    mName: String
    mLevel: int

  Instance Methods (5)
    init(): void
    get name(): String
    set name(value: String): void
    takeDamage(amount: Number): void
    serialize(): ByteArray
```

</details>

<details>
<summary><strong>flashkit strings</strong> — search string constants</summary>

```bash
flashkit strings application.swf                       # list all
flashkit strings application.swf -s config             # substring search
flashkit strings application.swf -s "http" -v          # with usage locations
flashkit strings application.swf -s "\\d+" -r          # regex search
flashkit strings application.swf -c                    # classify (URLs, debug markers)
```

</details>

<details>
<summary><strong>flashkit disasm</strong> — disassemble bytecode</summary>

```bash
flashkit disasm application.swf --class PlayerManager
flashkit disasm application.swf --method-index 42
```

</details>

<details>
<summary><strong>flashkit callers / callees</strong> — call graph queries</summary>

```bash
flashkit callers application.swf toString
flashkit callees application.swf PlayerManager.init
```

</details>

<details>
<summary><strong>flashkit refs</strong> — cross-references</summary>

```bash
flashkit refs application.swf Point
```

</details>

<details>
<summary><strong>flashkit tree</strong> — inheritance tree</summary>

```bash
flashkit tree application.swf BaseEntity              # descendants
flashkit tree application.swf PlayerManager -a        # ancestors
```

</details>

<details>
<summary><strong>flashkit packages / extract / build</strong></summary>

```bash
flashkit packages application.swf                     # list packages
flashkit extract application.swf -o ./output          # extract ABC blocks
flashkit build application.swf -o rebuilt.swf         # rebuild (compressed)
flashkit build application.swf -o out.swf -d          # rebuild (decompressed)
```

</details>

---

## Library reference

### Load and query

```python
from flashkit.workspace import Workspace

ws = Workspace()
ws.load_swf("application.swf")
ws.load_swz("module.swz")

print(ws.summary())

cls = ws.get_class("MyClass")
print(cls.name, cls.super_name, cls.interfaces)
print(cls.fields)   # list of FieldInfo
print(cls.methods)  # list of MethodInfoResolved

ws.find_classes(extends="Sprite")
ws.find_classes(package="com.example", is_interface=True)
```

<details>
<summary><strong>Parse SWF and ABC directly</strong></summary>

```python
from flashkit.swf import parse_swf, TAG_DO_ABC2
from flashkit.abc import parse_abc, serialize_abc

header, tags, version, length = parse_swf(swf_bytes)

for tag in tags:
    if tag.tag_type == TAG_DO_ABC2:
        null_idx = tag.payload.index(0, 4)
        abc = parse_abc(tag.payload[null_idx + 1:])
        print(f"{len(abc.instances)} classes, {len(abc.methods)} methods")

        # Round-trip fidelity: serialize(parse(data)) == data
        assert serialize_abc(abc) == tag.payload[null_idx + 1:]
```

</details>

<details>
<summary><strong>Build SWF programmatically</strong></summary>

```python
from flashkit.abc import AbcBuilder, serialize_abc
from flashkit.swf import SwfBuilder

b = AbcBuilder()
b.simple_class("Player", package="com.game",
               fields=[("hp", "int"), ("name", "String")])
b.script()
abc_bytes = serialize_abc(b.build())

swf = SwfBuilder(version=40, width=800, height=600, fps=30)
swf.add_abc("GameCode", abc_bytes)
swf_bytes = swf.build(compress=True)
```

</details>

<details>
<summary><strong>Analysis (inheritance, call graph, strings)</strong></summary>

```python
from flashkit.analysis import InheritanceGraph, CallGraph, StringIndex

graph = InheritanceGraph.from_classes(ws.classes)
graph.get_children("BaseEntity")
graph.get_all_parents("MyClass")
graph.get_implementors("ISerializable")

calls = CallGraph.from_workspace(ws)
calls.get_callers("toString")
calls.get_callees("MyClass.init")

strings = StringIndex.from_workspace(ws)
strings.search("config")
strings.url_strings()
strings.classes_using_string("http://example.com")
```

</details>

<details>
<summary><strong>Disassemble method bodies</strong></summary>

```python
from flashkit.abc import decode_instructions

for body in abc.method_bodies:
    for instr in decode_instructions(body.code):
        print(f"0x{instr.offset:04X}  {instr.mnemonic}  {instr.operands}")
```

</details>

---

## Project structure

```
flashkit/
  cli/           CLI (one module per command)
  swf/           SWF container (parse, build, tags)
  abc/           AVM2 bytecode (parse, write, disasm, builder)
  info/          Resolved class model (ClassInfo, FieldInfo, MethodInfo)
  workspace/     File loading and class index
  analysis/      Inheritance, call graph, references, strings
  search/        Unified query engine
```

## References

- [AVM2 Overview (Adobe)](https://www.adobe.com/content/dam/acom/en/devnet/pdf/avm2overview.pdf)
- [SWF File Format Specification](https://open-flash.github.io/mirrors/swf-spec-19.pdf)

## License

MIT
