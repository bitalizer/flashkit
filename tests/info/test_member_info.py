"""Tests for flashkit.info.member_info — multiname resolution, trait parsing, and resolve_traits."""

import pytest

from flashkit.abc.builder import AbcBuilder
from flashkit.abc.parser import parse_abc, write_u30
from flashkit.abc.writer import serialize_abc
from flashkit.abc.types import AbcFile, MultinameInfo, NamespaceInfo, MethodBodyInfo, TraitInfo
from flashkit.abc.constants import (
    CONSTANT_QName, CONSTANT_QNameA,
    CONSTANT_RTQName, CONSTANT_RTQNameA,
    CONSTANT_Multiname, CONSTANT_MultinameA,
    CONSTANT_TypeName,
    TRAIT_Slot, TRAIT_Const, TRAIT_Method, TRAIT_Getter, TRAIT_Setter,
    TRAIT_Class,
)
from flashkit.info.member_info import (
    resolve_multiname,
    resolve_multiname_full,
    parse_slot_trait,
    parse_method_trait,
    parse_class_trait,
    resolve_traits,
    build_method_body_map,
    FieldInfo,
    MethodInfoResolved,
)


# ── Helpers ────────────────────────────────────────────────────────────


def _make_abc(**overrides) -> AbcFile:
    """Build a minimal AbcFile with overridable pools."""
    defaults = dict(
        minor_version=16,
        major_version=46,
        int_pool=[0],
        uint_pool=[0],
        double_pool=[0.0],
        string_pool=[""],
        namespace_pool=[NamespaceInfo(kind=0, name=0)],
        ns_set_pool=[],
        multiname_pool=[MultinameInfo(kind=0)],
        methods=[],
        metadata=[],
        instances=[],
        classes=[],
        scripts=[],
        method_bodies=[],
    )
    defaults.update(overrides)
    return AbcFile(**defaults)


def _abc_with_strings_and_multinames(strings, multinames, namespace_pool=None):
    """Build an AbcFile with given string pool and multiname pool."""
    sp = [""] + list(strings)
    nsp = namespace_pool or [NamespaceInfo(kind=0, name=0)]
    mnp = [MultinameInfo(kind=0)] + list(multinames)
    return _make_abc(string_pool=sp, namespace_pool=nsp, multiname_pool=mnp)


# ── resolve_multiname ──────────────────────────────────────────────────


class TestResolveMultiname:
    def test_index_zero_returns_star(self):
        abc = _make_abc()
        assert resolve_multiname(abc, 0) == "*"

    def test_index_out_of_range_returns_star(self):
        abc = _make_abc()
        assert resolve_multiname(abc, 999) == "*"

    def test_qname(self):
        abc = _abc_with_strings_and_multinames(
            strings=["MyClass"],
            multinames=[MultinameInfo(kind=CONSTANT_QName, ns=0, name=1)],
        )
        assert resolve_multiname(abc, 1) == "MyClass"

    def test_qname_a(self):
        abc = _abc_with_strings_and_multinames(
            strings=["attr"],
            multinames=[MultinameInfo(kind=CONSTANT_QNameA, ns=0, name=1)],
        )
        assert resolve_multiname(abc, 1) == "attr"

    def test_rtqname(self):
        abc = _abc_with_strings_and_multinames(
            strings=["dynName"],
            multinames=[MultinameInfo(kind=CONSTANT_RTQName, name=1)],
        )
        assert resolve_multiname(abc, 1) == "dynName"

    def test_rtqname_a(self):
        abc = _abc_with_strings_and_multinames(
            strings=["dynAttr"],
            multinames=[MultinameInfo(kind=CONSTANT_RTQNameA, name=1)],
        )
        assert resolve_multiname(abc, 1) == "dynAttr"

    def test_multiname(self):
        abc = _abc_with_strings_and_multinames(
            strings=["multi"],
            multinames=[MultinameInfo(kind=CONSTANT_Multiname, name=1, ns_set=0)],
        )
        assert resolve_multiname(abc, 1) == "multi"

    def test_multiname_a(self):
        abc = _abc_with_strings_and_multinames(
            strings=["multiA"],
            multinames=[MultinameInfo(kind=CONSTANT_MultinameA, name=1, ns_set=0)],
        )
        assert resolve_multiname(abc, 1) == "multiA"

    def test_qname_with_zero_name_returns_fallback(self):
        abc = _abc_with_strings_and_multinames(
            strings=["unused"],
            multinames=[MultinameInfo(kind=CONSTANT_QName, ns=0, name=0)],
        )
        assert resolve_multiname(abc, 1) == "multiname[1]"

    def test_qname_with_name_out_of_range_returns_fallback(self):
        abc = _abc_with_strings_and_multinames(
            strings=["only"],
            multinames=[MultinameInfo(kind=CONSTANT_QName, ns=0, name=99)],
        )
        assert resolve_multiname(abc, 1) == "multiname[1]"

    def test_typename_single_param(self):
        """Vector.<int> style parameterized type."""
        param_data = bytes(write_u30(2))  # param index = mn[2] = "int"
        abc = _abc_with_strings_and_multinames(
            strings=["Vector", "int"],
            multinames=[
                MultinameInfo(kind=CONSTANT_QName, ns=0, name=1),   # mn[1] = Vector
                MultinameInfo(kind=CONSTANT_QName, ns=0, name=2),   # mn[2] = int
                MultinameInfo(kind=CONSTANT_TypeName, ns=1, name=1, data=param_data),  # mn[3] = Vector.<int>
            ],
        )
        assert resolve_multiname(abc, 3) == "Vector.<int>"

    def test_typename_multiple_params(self):
        """TypeName with two type parameters."""
        param_data = bytes(write_u30(2) + write_u30(3))
        abc = _abc_with_strings_and_multinames(
            strings=["Map", "String", "int"],
            multinames=[
                MultinameInfo(kind=CONSTANT_QName, ns=0, name=1),   # mn[1] = Map
                MultinameInfo(kind=CONSTANT_QName, ns=0, name=2),   # mn[2] = String
                MultinameInfo(kind=CONSTANT_QName, ns=0, name=3),   # mn[3] = int
                MultinameInfo(kind=CONSTANT_TypeName, ns=1, name=2, data=param_data),  # mn[4]
            ],
        )
        assert resolve_multiname(abc, 4) == "Map.<String, int>"

    def test_typename_no_params(self):
        """TypeName with zero params returns just the base name."""
        abc = _abc_with_strings_and_multinames(
            strings=["Base"],
            multinames=[
                MultinameInfo(kind=CONSTANT_QName, ns=0, name=1),   # mn[1] = Base
                MultinameInfo(kind=CONSTANT_TypeName, ns=1, name=0, data=b""),  # mn[2]
            ],
        )
        assert resolve_multiname(abc, 2) == "Base"


# ── resolve_multiname_full ─────────────────────────────────────────────


class TestResolveMultinameFull:
    def test_index_zero(self):
        abc = _make_abc()
        assert resolve_multiname_full(abc, 0) == ("", "*")

    def test_index_out_of_range(self):
        abc = _make_abc()
        assert resolve_multiname_full(abc, 999) == ("", "*")

    def test_qname_with_package(self):
        from flashkit.abc.constants import CONSTANT_PackageNamespace
        abc = _abc_with_strings_and_multinames(
            strings=["com.example", "Player"],
            namespace_pool=[
                NamespaceInfo(kind=0, name=0),  # ns[0] default
                NamespaceInfo(kind=CONSTANT_PackageNamespace, name=1),  # ns[1] = "com.example"
            ],
            multinames=[MultinameInfo(kind=CONSTANT_QName, ns=1, name=2)],
        )
        assert resolve_multiname_full(abc, 1) == ("com.example", "Player")

    def test_qname_no_package(self):
        abc = _abc_with_strings_and_multinames(
            strings=["Object"],
            multinames=[MultinameInfo(kind=CONSTANT_QName, ns=0, name=1)],
        )
        pkg, name = resolve_multiname_full(abc, 1)
        assert name == "Object"
        assert pkg == ""

    def test_rtqname_has_no_package(self):
        abc = _abc_with_strings_and_multinames(
            strings=["dynName"],
            multinames=[MultinameInfo(kind=CONSTANT_RTQName, name=1)],
        )
        pkg, name = resolve_multiname_full(abc, 1)
        assert name == "dynName"
        assert pkg == ""

    def test_multiname_has_no_package(self):
        abc = _abc_with_strings_and_multinames(
            strings=["multi"],
            multinames=[MultinameInfo(kind=CONSTANT_Multiname, name=1, ns_set=0)],
        )
        pkg, name = resolve_multiname_full(abc, 1)
        assert name == "multi"
        assert pkg == ""

    def test_qname_zero_name_returns_star(self):
        abc = _abc_with_strings_and_multinames(
            strings=["unused"],
            multinames=[MultinameInfo(kind=CONSTANT_QName, ns=0, name=0)],
        )
        _, name = resolve_multiname_full(abc, 1)
        assert name == "*"

    def test_typename_returns_full_name_and_base_package(self):
        from flashkit.abc.constants import CONSTANT_PackageNamespace
        param_data = bytes(write_u30(2))  # param index = mn[2] = "int"
        abc = _abc_with_strings_and_multinames(
            strings=["__AS3__.vec", "Vector", "int"],
            namespace_pool=[
                NamespaceInfo(kind=0, name=0),
                NamespaceInfo(kind=CONSTANT_PackageNamespace, name=1),  # ns[1] = "__AS3__.vec"
            ],
            multinames=[
                MultinameInfo(kind=CONSTANT_QName, ns=1, name=2),   # mn[1] = Vector (in __AS3__.vec)
                MultinameInfo(kind=CONSTANT_QName, ns=0, name=3),   # mn[2] = int
                MultinameInfo(kind=CONSTANT_TypeName, ns=1, name=1, data=param_data),  # mn[3]
            ],
        )
        pkg, name = resolve_multiname_full(abc, 3)
        assert name == "Vector.<int>"
        assert pkg == "__AS3__.vec"

    def test_typename_no_params_full(self):
        abc = _abc_with_strings_and_multinames(
            strings=["Base"],
            multinames=[
                MultinameInfo(kind=CONSTANT_QName, ns=0, name=1),   # mn[1] = Base
                MultinameInfo(kind=CONSTANT_TypeName, ns=1, name=0, data=b""),  # mn[2]
            ],
        )
        pkg, name = resolve_multiname_full(abc, 2)
        assert name == "Base"
        assert pkg == ""


# ── parse_slot_trait ───────────────────────────────────────────────────


class TestParseSlotTrait:
    def _build_slot_data(self, name_mn, kind, slot_id, type_mn, vindex):
        data = bytearray()
        data += write_u30(name_mn)
        data += bytes([kind])
        data += write_u30(slot_id)
        data += write_u30(type_mn)
        data += write_u30(vindex)
        return bytes(data)

    def test_basic_slot(self):
        data = self._build_slot_data(name_mn=3, kind=TRAIT_Slot, slot_id=1, type_mn=4, vindex=0)
        name_mn, slot_id, type_mn, default_val = parse_slot_trait(data)
        assert name_mn == 3
        assert slot_id == 1
        assert type_mn == 4
        assert default_val is None

    def test_slot_with_default(self):
        data = self._build_slot_data(name_mn=5, kind=TRAIT_Slot, slot_id=2, type_mn=6, vindex=7)
        name_mn, slot_id, type_mn, default_val = parse_slot_trait(data)
        assert name_mn == 5
        assert slot_id == 2
        assert type_mn == 6
        assert default_val == 7

    def test_const_trait(self):
        data = self._build_slot_data(name_mn=1, kind=TRAIT_Const, slot_id=0, type_mn=2, vindex=0)
        name_mn, slot_id, type_mn, default_val = parse_slot_trait(data)
        assert name_mn == 1
        assert default_val is None


# ── parse_method_trait ─────────────────────────────────────────────────


class TestParseMethodTrait:
    def _build_method_data(self, name_mn, kind, disp_id, method_idx):
        data = bytearray()
        data += write_u30(name_mn)
        data += bytes([kind])
        data += write_u30(disp_id)
        data += write_u30(method_idx)
        return bytes(data)

    def test_basic_method(self):
        data = self._build_method_data(name_mn=5, kind=TRAIT_Method, disp_id=0, method_idx=1)
        name_mn, disp_id, method_idx = parse_method_trait(data)
        assert name_mn == 5
        assert disp_id == 0
        assert method_idx == 1

    def test_getter(self):
        data = self._build_method_data(name_mn=3, kind=TRAIT_Getter, disp_id=0, method_idx=2)
        name_mn, disp_id, method_idx = parse_method_trait(data)
        assert name_mn == 3
        assert method_idx == 2

    def test_setter(self):
        data = self._build_method_data(name_mn=4, kind=TRAIT_Setter, disp_id=1, method_idx=3)
        name_mn, disp_id, method_idx = parse_method_trait(data)
        assert name_mn == 4
        assert disp_id == 1
        assert method_idx == 3


# ── parse_class_trait ──────────────────────────────────────────────────


class TestParseClassTrait:
    def test_basic_class_trait(self):
        data = bytearray()
        data += write_u30(1)            # name_mn
        data += bytes([TRAIT_Class])    # kind
        data += write_u30(2)            # slot_id
        data += write_u30(3)            # class_index
        name_mn, slot_id, class_idx = parse_class_trait(bytes(data))
        assert name_mn == 1
        assert slot_id == 2
        assert class_idx == 3


# ── resolve_traits (integration via AbcBuilder) ────────────────────────


class TestResolveTraits:
    def _build_abc_with_traits(self, fields=None, methods=None):
        """Build a round-tripped AbcFile with the given fields and methods as traits."""
        b = AbcBuilder()
        pub = b.package_namespace("")
        priv = b.private_namespace()

        traits = []
        if fields:
            for fname, ftype, is_const in fields:
                type_mn = b.qname(pub, ftype) if ftype else 0
                field_mn = b.qname(priv, fname)
                traits.append(b.trait_slot(field_mn, type_mn=type_mn, slot_id=len(traits) + 1, is_const=is_const))

        if methods:
            for mname, ret_type, params, kind in methods:
                ret_mn = b.qname(pub, ret_type) if ret_type else 0
                param_mns = [b.qname(pub, pt) for pt in params] if params else []
                m = b.method(params=param_mns, return_type=ret_mn)
                b.method_body(m, code=b.asm(b.op_getlocal_0(), b.op_pushscope(), b.op_returnvoid()))
                method_mn = b.qname(priv, mname)
                traits.append(b.trait_method(method_mn, m, kind=kind))

        cls_mn = b.qname(pub, "Dummy")
        obj_mn = b.qname(pub, "Object")
        b.define_class(name=cls_mn, super_name=obj_mn, instance_traits=traits)
        b.script()

        abc = b.build()
        raw = serialize_abc(abc)
        return parse_abc(raw)

    def test_resolve_field(self):
        abc = self._build_abc_with_traits(fields=[("hp", "int", False)])
        from flashkit.info.member_info import resolve_traits, build_method_body_map
        body_map = build_method_body_map(abc)
        fields, methods = resolve_traits(abc, abc.instances[0].traits, method_body_map=body_map)
        assert len(fields) == 1
        assert fields[0].name == "hp"
        assert fields[0].type_name == "int"
        assert fields[0].is_const is False

    def test_resolve_const_field(self):
        abc = self._build_abc_with_traits(fields=[("MAX", "int", True)])
        body_map = build_method_body_map(abc)
        fields, _ = resolve_traits(abc, abc.instances[0].traits, method_body_map=body_map)
        assert len(fields) == 1
        assert fields[0].name == "MAX"
        assert fields[0].is_const is True

    def test_resolve_method(self):
        abc = self._build_abc_with_traits(methods=[("attack", "void", ["int"], TRAIT_Method)])
        body_map = build_method_body_map(abc)
        _, methods = resolve_traits(abc, abc.instances[0].traits, method_body_map=body_map)
        assert len(methods) == 1
        assert methods[0].name == "attack"
        assert methods[0].return_type == "void"
        assert methods[0].param_types == ["int"]
        assert methods[0].is_getter is False
        assert methods[0].is_setter is False

    def test_resolve_getter_setter(self):
        abc = self._build_abc_with_traits(methods=[
            ("hp", "int", [], TRAIT_Getter),
            ("hp", "void", ["int"], TRAIT_Setter),
        ])
        body_map = build_method_body_map(abc)
        _, methods = resolve_traits(abc, abc.instances[0].traits, method_body_map=body_map)
        getters = [m for m in methods if m.is_getter]
        setters = [m for m in methods if m.is_setter]
        assert len(getters) == 1
        assert len(setters) == 1
        assert getters[0].return_type == "int"

    def test_resolve_static_flag(self):
        abc = self._build_abc_with_traits(fields=[("count", "int", False)])
        body_map = build_method_body_map(abc)
        fields, _ = resolve_traits(abc, abc.instances[0].traits, is_static=True, method_body_map=body_map)
        assert fields[0].is_static is True

    def test_resolve_method_body_index(self):
        abc = self._build_abc_with_traits(methods=[("run", "void", [], TRAIT_Method)])
        body_map = build_method_body_map(abc)
        _, methods = resolve_traits(abc, abc.instances[0].traits, method_body_map=body_map)
        assert methods[0].body_index >= 0

    def test_mixed_fields_and_methods(self):
        abc = self._build_abc_with_traits(
            fields=[("x", "Number", False), ("y", "Number", False)],
            methods=[("move", "void", ["Number", "Number"], TRAIT_Method)],
        )
        body_map = build_method_body_map(abc)
        fields, methods = resolve_traits(abc, abc.instances[0].traits, method_body_map=body_map)
        assert len(fields) == 2
        assert len(methods) == 1

    def test_empty_traits(self):
        abc = self._build_abc_with_traits()
        fields, methods = resolve_traits(abc, abc.instances[0].traits)
        assert fields == []
        assert methods == []


# ── build_method_body_map ──────────────────────────────────────────────


class TestBuildMethodBodyMap:
    def test_maps_method_to_body_index(self):
        abc = _make_abc(method_bodies=[
            MethodBodyInfo(method=5, max_stack=1, local_count=1,
                           init_scope_depth=0, max_scope_depth=1,
                           code=b"\x47", exceptions=[]),
            MethodBodyInfo(method=2, max_stack=1, local_count=1,
                           init_scope_depth=0, max_scope_depth=1,
                           code=b"\x47", exceptions=[]),
        ])
        m = build_method_body_map(abc)
        assert m[5] == 0
        assert m[2] == 1

    def test_empty_bodies(self):
        abc = _make_abc()
        m = build_method_body_map(abc)
        assert m == {}
