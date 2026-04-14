"""
Analysis services for ABC content.

This package provides graph-based and index-based analysis of the loaded
ABC bytecode. Each module builds a specific data structure from the parsed
ABC data that enables efficient queries.

Modules:
    inheritance: InheritanceGraph — class hierarchy (parent/child/interface).
    call_graph: CallGraph — method-to-method call edges from bytecode.
    references: ReferenceIndex — cross-references (field types, instantiations, imports).
    strings: StringIndex — string constant search and classification.
    field_access: FieldAccessIndex — field read/write tracking from bytecode.
    method_fingerprint: MethodFingerprint — structural features of method bodies.
    class_graph: ClassGraph — class-to-class reference graph with typed edges.
"""

from .inheritance import InheritanceGraph
from .call_graph import CallGraph, CallEdge
from .references import ReferenceIndex, Reference
from .strings import StringIndex, StringUsage
from .field_access import FieldAccessIndex, FieldAccess
from .method_fingerprint import (
    MethodFingerprint,
    extract_fingerprint,
    extract_constructor_fingerprint,
    extract_all_fingerprints,
)
from .class_graph import (
    ClassGraph,
    ClassNode,
    build_class_graph,
    FRAMEWORK_TYPES,
    CLASS_EDGE_KINDS,
)
from .unified import build_all_indexes

__all__ = [
    "InheritanceGraph",
    "CallGraph",
    "CallEdge",
    "ReferenceIndex",
    "Reference",
    "StringIndex",
    "StringUsage",
    "FieldAccessIndex",
    "FieldAccess",
    "MethodFingerprint",
    "extract_fingerprint",
    "extract_constructor_fingerprint",
    "extract_all_fingerprints",
    "ClassGraph",
    "ClassNode",
    "build_class_graph",
    "FRAMEWORK_TYPES",
    "CLASS_EDGE_KINDS",
    "build_all_indexes",
]
