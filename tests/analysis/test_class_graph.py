"""Tests for flashkit.analysis.class_graph — ClassGraph."""

import pytest

from flashkit.analysis.class_graph import ClassGraph


def test_class_graph_from_workspace(loaded_workspace):
    g = ClassGraph.from_workspace(loaded_workspace)
    assert "TestClass" in g.nodes
