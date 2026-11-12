"""MUTATION capability: governed natural operations.

Every handler here is atomic: repositories and kernels validate before their
first write, and the remaining steps (AVL rotations, relinking) cannot fail on
a valid structure. So no O(n) snapshot is taken per call. A snapshot is taken
only when ``verify_invariants`` is on (the post-check may fail after the
write) or for extension operations whose descriptor sets ``atomic=False``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..algorithms.bst import BSTAlgorithms
from ..algorithms.heaps import HeapAlgorithms
from ..algorithms.linked_list import LinkedListAlgorithms
from ..algorithms.trie import TrieAlgorithms
from ..algorithms.union_find import UnionFindAlgorithms
from ..core.errors import NotFoundError
from ..core.metadata import describe
from ..core.results import DSAExecutionContext
from ..structures.repositories import (
    GraphRepository,
    LinkedListRepository,
    QueueRepository,
    SequenceRepository,
    StackRepository,
    TreeRepository,
)
from .base import BaseDSACapability, operation


def _m(name: str, structure: str, time: str = "O(1)", **extra: Any) -> Any:
    return describe(name, "MUTATION", structure, time, "O(1)", mutates=True, **extra)


class MutationService(BaseDSACapability):
    capability = "MUTATION"

    def _changed(self, context: DSAExecutionContext, count: int = 1) -> None:
        context.affected_count += count

    # -- sequence
    @operation(_m("INSERT", "SEQUENCE", "O(n)"), requires=("value",))
    def _seq_insert(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> int:
        SequenceRepository().create(ctx.state, args["value"], args.get("index"))
        self._changed(ctx)
        return len(ctx.state.values)

    @operation(_m("UPDATE", "SEQUENCE"), requires=("index", "value"))
    def _seq_update(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> None:
        SequenceRepository().update(ctx.state, args["index"], args["value"])
        self._changed(ctx)

    @operation(_m("DELETE", "SEQUENCE", "O(n)"), requires=("index",))
    def _seq_delete(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> Any:
        value = SequenceRepository().delete(ctx.state, args["index"])
        self._changed(ctx)
        return value

    # -- linked list
    @operation(_m("APPEND", "LINKED_LIST"), requires=("value",))
    def _ll_append(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> str:
        node_id = LinkedListRepository().append(ctx.state, args["value"], args.get("node_id"))
        self._changed(ctx)
        return node_id

    @operation(_m("PREPEND", "LINKED_LIST"), requires=("value",))
    def _ll_prepend(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> str:
        node_id = LinkedListRepository().prepend(ctx.state, args["value"], args.get("node_id"))
        self._changed(ctx)
        return node_id

    @operation(_m("DELETE", "LINKED_LIST"), requires=("node_id",))
    def _ll_delete(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> Any:
        node = LinkedListRepository().delete(ctx.state, args["node_id"])
        self._changed(ctx)
        return node

    @operation(_m("REVERSE", "LINKED_LIST", "O(n)"))
    def _ll_reverse(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> None:
        LinkedListAlgorithms.reverse(ctx.state)
        self._changed(ctx, ctx.state.size)

    # -- stack / queue (capacity config is the fallback bound)
    @operation(_m("PUSH", "STACK"), requires=("value",))
    def _push(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> None:
        StackRepository().push(ctx.state, args["value"], capacity=self._setting(ctx, "capacity", args))
        self._changed(ctx)

    @operation(_m("POP", "STACK"))
    def _pop(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> Any:
        value = StackRepository().pop(ctx.state)
        self._changed(ctx)
        return value

    @operation(_m("ENQUEUE", "QUEUE"), requires=("value",))
    def _enqueue(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> None:
        QueueRepository().enqueue(ctx.state, args["value"], capacity=self._setting(ctx, "capacity", args))
        self._changed(ctx)

    @operation(_m("DEQUEUE", "QUEUE"))
    def _dequeue(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> Any:
        value = QueueRepository().dequeue(ctx.state)
        self._changed(ctx)
        return value

    # -- tree
    @operation(_m("ADD_ROOT", "TREE"), requires=("node_id", "value"))
    def _add_root(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> None:
        TreeRepository().add_root(ctx.state, args["node_id"], args["value"])
        self._changed(ctx)

    @operation(_m("ADD_CHILD", "TREE"), requires=("parent_id", "node_id", "value"))
    def _add_child(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> bool:
        added = TreeRepository().add_child(
            ctx.state,
            args["parent_id"],
            args["node_id"],
            args["value"],
            on_duplicate=self._setting(ctx, "duplicate_policy", args),
        )
        self._changed(ctx, 1 if added else 0)
        return added

    @operation(_m("DELETE_SUBTREE", "TREE", "O(subtree)"), requires=("node_id",))
    def _delete_subtree(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> list[str]:
        removed = TreeRepository().delete_subtree(ctx.state, args["node_id"])
        self._changed(ctx, len(removed))
        return removed

    # -- BST (bst_balance_policy selects plain or AVL kernels)
    @operation(_m("INSERT", "BST", "O(h)"), requires=("value",))
    def _bst_insert(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> str:
        avl = self._setting(ctx, "bst_balance_policy", args) == "avl"
        kernel = BSTAlgorithms.insert_avl if avl else BSTAlgorithms.insert
        size = len(ctx.state.nodes)
        node_id = kernel(
            ctx.state,
            args["value"],
            key=args.get("key"),
            node_id=args.get("node_id"),
            on_duplicate=self._setting(ctx, "duplicate_policy", args),
        )
        self._changed(ctx, len(ctx.state.nodes) - size)
        return node_id

    @operation(_m("DELETE", "BST", "O(h)"), requires=("target",))
    def _bst_delete(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> Any:
        avl = self._setting(ctx, "bst_balance_policy", args) == "avl"
        node = BSTAlgorithms.delete(ctx.state, args["target"], key=args.get("key"), rebalance=avl)
        self._changed(ctx)
        return node

    # -- trie
    @operation(_m("INSERT", "TRIE", "O(L)"), requires=("word",))
    def _trie_insert(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> bool:
        added = TrieAlgorithms.insert(ctx.state, args["word"])
        self._changed(ctx, int(added))
        return added

    @operation(_m("DELETE", "TRIE", "O(L)"), requires=("word",))
    def _trie_delete(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> bool:
        if not TrieAlgorithms.delete(ctx.state, args["word"]):
            raise NotFoundError(f"word not found: {args['word']!r}")
        self._changed(ctx)
        return True

    # -- graph
    @operation(_m("ADD_VERTEX", "GRAPH"), requires=("vertex_id", "value"))
    def _add_vertex(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> bool:
        added = GraphRepository().add_vertex(
            ctx.state,
            args["vertex_id"],
            args["value"],
            on_duplicate=self._setting(ctx, "duplicate_policy", args),
        )
        self._changed(ctx, int(added))
        return added

    @operation(_m("ADD_EDGE", "GRAPH"), requires=("source", "target"))
    def _add_edge(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> None:
        GraphRepository().add_edge(ctx.state, args["source"], args["target"], args.get("weight", 1.0))
        self._changed(ctx)

    @operation(_m("REMOVE_EDGE", "GRAPH"), requires=("source", "target"))
    def _remove_edge(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> None:
        GraphRepository().remove_edge(ctx.state, args["source"], args["target"])
        self._changed(ctx)

    @operation(_m("REMOVE_VERTEX", "GRAPH", "O(V+E)"), requires=("vertex_id",))
    def _remove_vertex(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> None:
        GraphRepository().remove_vertex(ctx.state, args["vertex_id"])
        self._changed(ctx)

    # -- heap
    @operation(_m("PUSH", "HEAP", "O(log n)"), requires=("value",))
    def _heap_push(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> int:
        HeapAlgorithms.push(ctx.state, args["value"])
        self._changed(ctx)
        return len(ctx.state.values)

    @operation(_m("POP", "HEAP", "O(log n)"))
    def _heap_pop(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> Any:
        value = HeapAlgorithms.pop(ctx.state)
        self._changed(ctx)
        return value

    # -- union-find
    @operation(_m("ADD", "UNION_FIND"), requires=("element",))
    def _uf_add(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> bool:
        added = UnionFindAlgorithms.make_set(ctx.state, args["element"])
        if added:
            self._changed(ctx)
        return added

    @operation(_m("ADD_ALL", "UNION_FIND", "O(n)"), requires=("elements",))
    def _uf_add_all(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> int:
        added = UnionFindAlgorithms.add_all(ctx.state, args["elements"])
        if added:
            self._changed(ctx, added)
        return added

    @operation(_m("GROUP_BY_KEYS", "UNION_FIND", "O(n * k)"), requires=("elements", "keys"))
    def _uf_group_by_keys(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> list[list[Any]]:
        groups = UnionFindAlgorithms.group_by_keys(
            ctx.state, args["elements"], args["keys"], args.get("element_id")
        )
        self._changed(ctx)
        return groups

    @operation(_m("UNION", "UNION_FIND", "O(log n)"), requires=("left", "right"))
    def _uf_union(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> bool:
        merged = UnionFindAlgorithms.union(ctx.state, args["left"], args["right"])
        if merged:
            self._changed(ctx)
        return merged
