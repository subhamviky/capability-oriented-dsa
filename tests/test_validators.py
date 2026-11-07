"""Validators must report each kind of corruption (negative cases)."""

from __future__ import annotations

from collections import deque
from types import ModuleType

import pytest


def violations(validator: object, state: object) -> str:
    report = validator.validate(state)
    assert not report.valid
    return "; ".join(report.violations)


def test_linked_list_corruptions(dsa: ModuleType) -> None:
    v = dsa.LinkedListValidator()
    node = dsa.LinkedNode
    assert "empty list" in violations(v, dsa.LinkedListState(head_id="x"))
    mismatched = dsa.LinkedListState(nodes={"a": node("b", 1)}, head_id="a", tail_id="a", size=1)
    assert "does not match node_id" in violations(v, mismatched)
    dangling = dsa.LinkedListState(nodes={"a": node("a", 1, next_id="zz")}, head_id="a", tail_id="a", size=1)
    assert "missing node reference" in violations(v, dangling)
    cyclic = dsa.LinkedListState(
        nodes={"a": node("a", 1, next_id="b"), "b": node("b", 2, next_id="a", previous_id="a")},
        head_id="a",
        tail_id="b",
        size=2,
    )
    assert "cycle" in violations(v, cyclic)
    with pytest.raises(dsa.InvariantViolationError):
        v.validate(cyclic, raise_on_error=True)


def test_tree_corruptions(dsa: ModuleType) -> None:
    v = dsa.TreeValidator()
    assert "empty tree" in violations(v, dsa.TreeState(root_id="r"))
    assert "root is missing" in violations(v, dsa.TreeState(values={"a": 1}, root_id="r"))
    state = dsa.TreeState(
        values={"r": 1, "a": 2, "x": 3},
        children={"r": ["a", "ghost"], "a": [], "orphan": []},
        parent={"r": "a", "a": "r", "zz": "r"},
        root_id="r",
    )
    text = violations(v, state)
    for fragment in (
        "root parent",
        "unknown node: zz",
        "unknown node: orphan",
        "missing child",
        "not all nodes",
    ):
        assert fragment in text


def test_bst_corruptions(dsa: ModuleType) -> None:
    v = dsa.BSTValidator()
    node = dsa.BSTNode
    assert "root is None" in violations(v, dsa.BSTState(nodes={"a": node("a", 1)}))
    assert "root is missing" in violations(v, dsa.BSTState(root_id="x"))
    bad_order = dsa.BSTState(
        nodes={"r": node("r", 5, left_id="l", height=2), "l": node("l", 9, parent_id="r")}, root_id="r"
    )
    assert "ordering violated" in violations(v, bad_order)
    bad_links = dsa.BSTState(
        nodes={"r": node("r", 5, right_id="x", height=1, parent_id="p"), "x": node("x", 9)}, root_id="r"
    )
    text = violations(v, bad_links)
    assert "root parent" in text and "parent mismatch" in text and "stored height" in text
    dangling = dsa.BSTState(nodes={"r": node("r", 5, left_id="ghost", height=2)}, root_id="r")
    assert "missing node" in violations(v, dangling)


def test_trie_and_container_corruptions(dsa: ModuleType) -> None:
    trie = dsa.TrieState(word_count=3)
    trie.root.children["ab"] = dsa.TrieNode(terminal=True)
    text = violations(dsa.TrieValidator(), trie)
    assert "one character" in text and "word_count" in text
    assert "exceeds capacity" in violations(dsa.ContainerValidator(), dsa.StackState([1, 2], capacity=1))
    assert "capacity must be" in violations(dsa.ContainerValidator(), dsa.QueueState(deque(), capacity=-5))


def test_graph_corruptions(dsa: ModuleType) -> None:
    state = dsa.GraphState(values={"a": 1}, adjacency={"a": {"b": True}, "ghost": {}}, directed=True)
    text = violations(dsa.GraphValidator(), state)
    assert "source missing" in text and "target missing" in text and "not a number" in text


def test_governed_validation_reports_without_raising(dsa: ModuleType) -> None:
    state = dsa.StackState([1, 2], capacity=1)
    result = dsa.DSAFacade().execute(
        structure_type="STACK", capability="VALIDATION", operation="VALIDATE", state=state
    )
    assert not result.data.valid
    assert result.messages[0].code == "INVARIANT_VIOLATIONS"
