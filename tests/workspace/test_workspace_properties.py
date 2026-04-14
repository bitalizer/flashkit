"""Tests for Workspace lazy analysis properties (1.2.0 API)."""

from flashkit.analysis.call_graph import CallGraph
from flashkit.analysis.class_graph import ClassGraph
from flashkit.analysis.field_access import FieldAccessIndex
from flashkit.analysis.inheritance import InheritanceGraph
from flashkit.analysis.references import ReferenceIndex
from flashkit.analysis.strings import StringIndex


def test_class_graph_property(loaded_workspace):
    g = loaded_workspace.class_graph
    assert isinstance(g, ClassGraph)
    assert loaded_workspace.class_graph is g  # cached


def test_call_graph_property(loaded_workspace):
    g = loaded_workspace.call_graph
    assert isinstance(g, CallGraph)
    assert loaded_workspace.call_graph is g


def test_reference_index_property(loaded_workspace):
    idx = loaded_workspace.reference_index
    assert isinstance(idx, ReferenceIndex)
    assert loaded_workspace.reference_index is idx


def test_string_index_property(loaded_workspace):
    idx = loaded_workspace.string_index
    assert isinstance(idx, StringIndex)
    assert loaded_workspace.string_index is idx


def test_field_access_index_property(loaded_workspace):
    idx = loaded_workspace.field_access_index
    assert isinstance(idx, FieldAccessIndex)
    assert loaded_workspace.field_access_index is idx


def test_inheritance_property(loaded_workspace):
    g = loaded_workspace.inheritance
    assert isinstance(g, InheritanceGraph)
    assert loaded_workspace.inheritance is g
