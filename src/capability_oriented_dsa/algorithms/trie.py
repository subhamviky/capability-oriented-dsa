"""Trie kernels."""

from __future__ import annotations

from ..structures.states import TrieNode, TrieState


class TrieAlgorithms:
    @staticmethod
    def insert(state: TrieState, word: str) -> bool:
        """Insert ``word``. Returns False if it was already present."""
        node = state.root
        for char in word:
            node = node.children.setdefault(char, TrieNode())
        if node.terminal:
            return False
        node.terminal = True
        state.word_count += 1
        return True

    @staticmethod
    def _find(state: TrieState, prefix: str) -> TrieNode | None:
        node = state.root
        for char in prefix:
            child = node.children.get(char)
            if child is None:
                return None
            node = child
        return node

    @staticmethod
    def search(state: TrieState, word: str) -> bool:
        node = TrieAlgorithms._find(state, word)
        return node is not None and node.terminal

    @staticmethod
    def starts_with(state: TrieState, prefix: str) -> bool:
        return TrieAlgorithms._find(state, prefix) is not None

    @staticmethod
    def autocomplete(state: TrieState, prefix: str, limit: int = -1) -> list[str]:
        """Words with ``prefix`` in lexicographic order; iterative, stops at ``limit``."""
        node = TrieAlgorithms._find(state, prefix)
        if node is None:
            return []
        result: list[str] = []
        stack: list[tuple[TrieNode, str]] = [(node, prefix)]
        while stack and not (0 <= limit <= len(result)):
            current, word = stack.pop()
            if current.terminal:
                result.append(word)
            for char in sorted(current.children, reverse=True):
                stack.append((current.children[char], word + char))
        return result

    @staticmethod
    def delete(state: TrieState, word: str) -> bool:
        """Remove ``word`` and prune now-empty branches. Returns False if absent."""
        path: list[tuple[TrieNode, str]] = []
        node = state.root
        for char in word:
            child = node.children.get(char)
            if child is None:
                return False
            path.append((node, char))
            node = child
        if not node.terminal:
            return False
        node.terminal = False
        state.word_count -= 1
        for parent, char in reversed(path):
            child = parent.children[char]
            if child.terminal or child.children:
                break
            del parent.children[char]
        return True
