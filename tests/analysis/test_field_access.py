"""Tests for flashkit.analysis.field_access — FieldAccessIndex."""

import pytest

from flashkit.abc.builder import AbcBuilder
from flashkit.abc.parser import parse_abc
from flashkit.abc.writer import serialize_abc
from flashkit.info.class_info import build_all_classes
from flashkit.analysis.field_access import FieldAccessIndex


def _build_field_index(setup_fn):
    """Helper: run setup_fn with an AbcBuilder, build, and create FieldAccessIndex.

    setup_fn receives (builder, pub_ns, priv_ns) and should define classes.
    Returns (FieldAccessIndex, classes).
    """
    b = AbcBuilder()
    pub = b.package_namespace("")
    priv = b.private_namespace()
    setup_fn(b, pub, priv)
    b.script()

    abc = b.build()
    raw = serialize_abc(abc)
    abc2 = parse_abc(raw)
    classes = build_all_classes(abc2)
    index = FieldAccessIndex.from_abc(abc2, classes)
    return index, classes


class TestFieldWrite:
    def test_setproperty_tracked(self):
        """OP_setproperty on a field is tracked as a write."""
        def setup(b, pub, priv):
            cls_mn = b.qname(pub, "Entity")
            field_mn = b.qname(priv, "health")
            int_mn = b.qname(pub, "int")
            m = b.method()
            b.method_body(m, code=b.asm(
                b.op_getlocal_0(), b.op_pushscope(),
                b.op_getlocal_0(),
                b.op_pushbyte(100),
                b.op_setproperty(field_mn),
                b.op_returnvoid(),
            ), max_stack=2, local_count=1)
            method_mn = b.qname(priv, "reset")
            b.define_class(
                name=cls_mn, super_name=0,
                instance_traits=[
                    b.trait_slot(field_mn, type_mn=int_mn),
                    b.trait_method(method_mn, m),
                ])

        idx, _ = _build_field_index(setup)
        writers = idx.writers_of("Entity", "health")
        assert "reset" in writers

    def test_initproperty_tracked(self):
        """OP_initproperty on a field is tracked as an init (write)."""
        def setup(b, pub, priv):
            cls_mn = b.qname(pub, "Config")
            field_mn = b.qname(priv, "version")
            int_mn = b.qname(pub, "int")
            # Constructor that initializes field
            ctor = b.method()
            b.method_body(ctor, code=b.asm(
                b.op_getlocal_0(), b.op_pushscope(),
                b.op_getlocal_0(),
                b.op_constructsuper(0),
                b.op_getlocal_0(),
                b.op_pushbyte(1),
                b.op_initproperty(field_mn),
                b.op_returnvoid(),
            ), max_stack=2, local_count=1)
            b.define_class(
                name=cls_mn, super_name=0, constructor=ctor,
                instance_traits=[b.trait_slot(field_mn, type_mn=int_mn)])

        idx, _ = _build_field_index(setup)
        writers = idx.writers_of("Config", "version")
        assert "<init>" in writers


class TestFieldRead:
    def test_getproperty_tracked(self):
        """OP_getproperty on a field is tracked as a read."""
        def setup(b, pub, priv):
            cls_mn = b.qname(pub, "Player")
            field_mn = b.qname(priv, "score")
            int_mn = b.qname(pub, "int")
            m = b.method(return_type=int_mn)
            b.method_body(m, code=b.asm(
                b.op_getlocal_0(), b.op_pushscope(),
                b.op_getlocal_0(),
                b.op_getproperty(field_mn),
                b.op_returnvalue(),
            ), max_stack=2, local_count=1)
            method_mn = b.qname(priv, "getScore")
            b.define_class(
                name=cls_mn, super_name=0,
                instance_traits=[
                    b.trait_slot(field_mn, type_mn=int_mn),
                    b.trait_method(method_mn, m),
                ])

        idx, _ = _build_field_index(setup)
        readers = idx.readers_of("Player", "score")
        assert "getScore" in readers

    def test_read_not_in_writers(self):
        """A read should not appear in writers_of."""
        def setup(b, pub, priv):
            cls_mn = b.qname(pub, "Item")
            field_mn = b.qname(priv, "name")
            str_mn = b.qname(pub, "String")
            m = b.method(return_type=str_mn)
            b.method_body(m, code=b.asm(
                b.op_getlocal_0(), b.op_pushscope(),
                b.op_getlocal_0(),
                b.op_getproperty(field_mn),
                b.op_returnvalue(),
            ), max_stack=2, local_count=1)
            method_mn = b.qname(priv, "getName")
            b.define_class(
                name=cls_mn, super_name=0,
                instance_traits=[
                    b.trait_slot(field_mn, type_mn=str_mn),
                    b.trait_method(method_mn, m),
                ])

        idx, _ = _build_field_index(setup)
        writers = idx.writers_of("Item", "name")
        assert "getName" not in writers


class TestFieldsReadWrittenBy:
    def test_fields_written_by_method(self):
        """fields_written_by returns all fields a method writes."""
        def setup(b, pub, priv):
            cls_mn = b.qname(pub, "State")
            f1 = b.qname(priv, "x")
            f2 = b.qname(priv, "y")
            int_mn = b.qname(pub, "int")
            m = b.method()
            b.method_body(m, code=b.asm(
                b.op_getlocal_0(), b.op_pushscope(),
                b.op_getlocal_0(), b.op_pushbyte(0),
                b.op_setproperty(f1),
                b.op_getlocal_0(), b.op_pushbyte(0),
                b.op_setproperty(f2),
                b.op_returnvoid(),
            ), max_stack=2, local_count=1)
            method_mn = b.qname(priv, "reset")
            b.define_class(
                name=cls_mn, super_name=0,
                instance_traits=[
                    b.trait_slot(f1, type_mn=int_mn),
                    b.trait_slot(f2, type_mn=int_mn),
                    b.trait_method(method_mn, m),
                ])

        idx, _ = _build_field_index(setup)
        written = idx.fields_written_by("State", "reset")
        assert "x" in written
        assert "y" in written

    def test_fields_read_by_method(self):
        """fields_read_by returns all fields a method reads."""
        def setup(b, pub, priv):
            cls_mn = b.qname(pub, "Pos")
            f1 = b.qname(priv, "px")
            f2 = b.qname(priv, "py")
            int_mn = b.qname(pub, "int")
            m = b.method()
            b.method_body(m, code=b.asm(
                b.op_getlocal_0(), b.op_pushscope(),
                b.op_getlocal_0(), b.op_getproperty(f1),
                b.op_getlocal_0(), b.op_getproperty(f2),
                b.op_pop(), b.op_pop(),
                b.op_returnvoid(),
            ), max_stack=2, local_count=1)
            method_mn = b.qname(priv, "update")
            b.define_class(
                name=cls_mn, super_name=0,
                instance_traits=[
                    b.trait_slot(f1, type_mn=int_mn),
                    b.trait_slot(f2, type_mn=int_mn),
                    b.trait_method(method_mn, m),
                ])

        idx, _ = _build_field_index(setup)
        read_fields = idx.fields_read_by("Pos", "update")
        assert "px" in read_fields
        assert "py" in read_fields

    def test_fields_accessed_by(self):
        """fields_accessed_by includes both reads and writes."""
        def setup(b, pub, priv):
            cls_mn = b.qname(pub, "Counter")
            field_mn = b.qname(priv, "count")
            int_mn = b.qname(pub, "int")
            m = b.method()
            b.method_body(m, code=b.asm(
                b.op_getlocal_0(), b.op_pushscope(),
                # Read count
                b.op_getlocal_0(), b.op_getproperty(field_mn),
                b.op_pop(),
                # Write count
                b.op_getlocal_0(), b.op_pushbyte(1),
                b.op_setproperty(field_mn),
                b.op_returnvoid(),
            ), max_stack=2, local_count=1)
            method_mn = b.qname(priv, "increment")
            b.define_class(
                name=cls_mn, super_name=0,
                instance_traits=[
                    b.trait_slot(field_mn, type_mn=int_mn),
                    b.trait_method(method_mn, m),
                ])

        idx, _ = _build_field_index(setup)
        accessed = idx.fields_accessed_by("Counter", "increment")
        assert "count" in accessed


class TestConstructor:
    def test_constructor_assignments(self):
        """constructor_assignments returns fields set in <init>."""
        def setup(b, pub, priv):
            cls_mn = b.qname(pub, "Obj")
            f1 = b.qname(priv, "alpha")
            f2 = b.qname(priv, "beta")
            int_mn = b.qname(pub, "int")
            ctor = b.method()
            b.method_body(ctor, code=b.asm(
                b.op_getlocal_0(), b.op_pushscope(),
                b.op_getlocal_0(), b.op_constructsuper(0),
                # Set alpha first, then beta
                b.op_getlocal_0(), b.op_pushbyte(1),
                b.op_initproperty(f1),
                b.op_getlocal_0(), b.op_pushbyte(2),
                b.op_initproperty(f2),
                b.op_returnvoid(),
            ), max_stack=2, local_count=1)
            b.define_class(
                name=cls_mn, super_name=0, constructor=ctor,
                instance_traits=[
                    b.trait_slot(f1, type_mn=int_mn),
                    b.trait_slot(f2, type_mn=int_mn),
                ])

        idx, _ = _build_field_index(setup)
        assignments = idx.constructor_assignments("Obj")
        assert assignments == ["alpha", "beta"]

    def test_constructor_assignments_preserves_order(self):
        """Assignment order matches bytecode order."""
        def setup(b, pub, priv):
            cls_mn = b.qname(pub, "Ordered")
            fz = b.qname(priv, "z")
            fa = b.qname(priv, "a")
            int_mn = b.qname(pub, "int")
            ctor = b.method()
            b.method_body(ctor, code=b.asm(
                b.op_getlocal_0(), b.op_pushscope(),
                b.op_getlocal_0(), b.op_constructsuper(0),
                # z before a
                b.op_getlocal_0(), b.op_pushbyte(0),
                b.op_initproperty(fz),
                b.op_getlocal_0(), b.op_pushbyte(0),
                b.op_initproperty(fa),
                b.op_returnvoid(),
            ), max_stack=2, local_count=1)
            b.define_class(
                name=cls_mn, super_name=0, constructor=ctor,
                instance_traits=[
                    b.trait_slot(fz, type_mn=int_mn),
                    b.trait_slot(fa, type_mn=int_mn),
                ])

        idx, _ = _build_field_index(setup)
        assignments = idx.constructor_assignments("Ordered")
        assert assignments == ["z", "a"]

    def test_constructor_reads(self):
        """constructor_reads returns fields read in <init>."""
        def setup(b, pub, priv):
            cls_mn = b.qname(pub, "Derived")
            field_mn = b.qname(priv, "base")
            int_mn = b.qname(pub, "int")
            ctor = b.method()
            b.method_body(ctor, code=b.asm(
                b.op_getlocal_0(), b.op_pushscope(),
                b.op_getlocal_0(), b.op_constructsuper(0),
                b.op_getlocal_0(), b.op_getproperty(field_mn),
                b.op_pop(),
                b.op_returnvoid(),
            ), max_stack=2, local_count=1)
            b.define_class(
                name=cls_mn, super_name=0, constructor=ctor,
                instance_traits=[b.trait_slot(field_mn, type_mn=int_mn)])

        idx, _ = _build_field_index(setup)
        reads = idx.constructor_reads("Derived")
        assert "base" in reads


class TestClassLevel:
    def test_all_fields_in_class(self):
        """all_fields_in_class returns all fields accessed by any method."""
        def setup(b, pub, priv):
            cls_mn = b.qname(pub, "Multi")
            f1 = b.qname(priv, "a")
            f2 = b.qname(priv, "b")
            int_mn = b.qname(pub, "int")
            m1 = b.method()
            b.method_body(m1, code=b.asm(
                b.op_getlocal_0(), b.op_pushscope(),
                b.op_getlocal_0(), b.op_getproperty(f1),
                b.op_pop(), b.op_returnvoid(),
            ), max_stack=2, local_count=1)
            m2 = b.method()
            b.method_body(m2, code=b.asm(
                b.op_getlocal_0(), b.op_pushscope(),
                b.op_getlocal_0(), b.op_pushbyte(0),
                b.op_setproperty(f2),
                b.op_returnvoid(),
            ), max_stack=2, local_count=1)
            mn1 = b.qname(priv, "readA")
            mn2 = b.qname(priv, "writeB")
            b.define_class(
                name=cls_mn, super_name=0,
                instance_traits=[
                    b.trait_slot(f1, type_mn=int_mn),
                    b.trait_slot(f2, type_mn=int_mn),
                    b.trait_method(mn1, m1),
                    b.trait_method(mn2, m2),
                ])

        idx, _ = _build_field_index(setup)
        fields = idx.all_fields_in_class("Multi")
        assert "a" in fields
        assert "b" in fields

    def test_field_access_summary(self):
        """field_access_summary returns readers and writers per field."""
        def setup(b, pub, priv):
            cls_mn = b.qname(pub, "Summary")
            field_mn = b.qname(priv, "val")
            int_mn = b.qname(pub, "int")
            reader = b.method(return_type=int_mn)
            b.method_body(reader, code=b.asm(
                b.op_getlocal_0(), b.op_pushscope(),
                b.op_getlocal_0(), b.op_getproperty(field_mn),
                b.op_returnvalue(),
            ), max_stack=2, local_count=1)
            writer = b.method()
            b.method_body(writer, code=b.asm(
                b.op_getlocal_0(), b.op_pushscope(),
                b.op_getlocal_0(), b.op_pushbyte(42),
                b.op_setproperty(field_mn),
                b.op_returnvoid(),
            ), max_stack=2, local_count=1)
            rmn = b.qname(priv, "getVal")
            wmn = b.qname(priv, "setVal")
            b.define_class(
                name=cls_mn, super_name=0,
                instance_traits=[
                    b.trait_slot(field_mn, type_mn=int_mn),
                    b.trait_method(rmn, reader),
                    b.trait_method(wmn, writer),
                ])

        idx, _ = _build_field_index(setup)
        summary = idx.field_access_summary("Summary")
        assert "val" in summary
        assert "getVal" in summary["val"]["readers"]
        assert "setVal" in summary["val"]["writers"]


class TestProperties:
    def test_total_accesses(self):
        def setup(b, pub, priv):
            cls_mn = b.qname(pub, "Props")
            field_mn = b.qname(priv, "data")
            int_mn = b.qname(pub, "int")
            m = b.method()
            b.method_body(m, code=b.asm(
                b.op_getlocal_0(), b.op_pushscope(),
                b.op_getlocal_0(), b.op_getproperty(field_mn),
                b.op_pop(),
                b.op_getlocal_0(), b.op_pushbyte(0),
                b.op_setproperty(field_mn),
                b.op_returnvoid(),
            ), max_stack=2, local_count=1)
            method_mn = b.qname(priv, "process")
            b.define_class(
                name=cls_mn, super_name=0,
                instance_traits=[
                    b.trait_slot(field_mn, type_mn=int_mn),
                    b.trait_method(method_mn, m),
                ])

        idx, _ = _build_field_index(setup)
        assert idx.total_accesses >= 2
        assert idx.total_reads >= 1
        assert idx.total_writes >= 1

    def test_access_count(self):
        def setup(b, pub, priv):
            cls_mn = b.qname(pub, "Counted")
            field_mn = b.qname(priv, "n")
            int_mn = b.qname(pub, "int")
            m = b.method()
            b.method_body(m, code=b.asm(
                b.op_getlocal_0(), b.op_pushscope(),
                b.op_getlocal_0(), b.op_getproperty(field_mn),
                b.op_pop(),
                b.op_getlocal_0(), b.op_getproperty(field_mn),
                b.op_pop(),
                b.op_returnvoid(),
            ), max_stack=2, local_count=1)
            method_mn = b.qname(priv, "readTwice")
            b.define_class(
                name=cls_mn, super_name=0,
                instance_traits=[
                    b.trait_slot(field_mn, type_mn=int_mn),
                    b.trait_method(method_mn, m),
                ])

        idx, _ = _build_field_index(setup)
        assert idx.access_count("Counted", "n") >= 2


class TestNameResolution:
    def test_simple_name_match(self):
        """Queries work with simple class names even when stored qualified."""
        def setup(b, pub, priv):
            pkg_ns = b.package_namespace("com.game")
            cls_mn = b.qname(pkg_ns, "Hero")
            field_mn = b.qname(priv, "hp")
            int_mn = b.qname(pub, "int")
            m = b.method()
            b.method_body(m, code=b.asm(
                b.op_getlocal_0(), b.op_pushscope(),
                b.op_getlocal_0(), b.op_getproperty(field_mn),
                b.op_pop(), b.op_returnvoid(),
            ), max_stack=2, local_count=1)
            method_mn = b.qname(priv, "check")
            b.define_class(
                name=cls_mn, super_name=0,
                instance_traits=[
                    b.trait_slot(field_mn, type_mn=int_mn),
                    b.trait_method(method_mn, m),
                ])

        idx, _ = _build_field_index(setup)
        # Should work with simple name
        readers = idx.readers_of("Hero", "hp")
        assert "check" in readers
