"""Sequence, stack-based and queue-based kernels."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Sequence
from typing import ClassVar

from ..core.errors import InvalidInputError


class SequenceAlgorithms:
    @staticmethod
    def two_sum(values: Sequence[int], target: int) -> tuple[int, int] | None:
        seen: dict[int, int] = {}
        for index, value in enumerate(values):
            if target - value in seen:
                return seen[target - value], index
            seen.setdefault(value, index)
        return None

    @staticmethod
    def maximum_subarray(values: Sequence[int]) -> int:
        """Kadane's algorithm."""
        if not values:
            raise InvalidInputError("values must not be empty")
        best = current = values[0]
        for value in values[1:]:
            current = max(value, current + value)
            best = max(best, current)
        return best

    @staticmethod
    def prefix_sums(values: Sequence[int]) -> list[int]:
        out = [0]
        for value in values:
            out.append(out[-1] + value)
        return out


class StackAlgorithms:
    PAIRS: ClassVar[dict[str, str]] = {")": "(", "]": "[", "}": "{"}

    @staticmethod
    def balanced_brackets(text: str) -> bool:
        stack: list[str] = []
        for char in text:
            if char in "([{":
                stack.append(char)
            elif char in StackAlgorithms.PAIRS and (not stack or stack.pop() != StackAlgorithms.PAIRS[char]):
                return False
        return not stack

    @staticmethod
    def evaluate_postfix(tokens: Iterable[str]) -> float:
        stack: list[float] = []
        for token in tokens:
            if token not in {"+", "-", "*", "/"}:
                try:
                    stack.append(float(token))
                except ValueError as exc:
                    raise InvalidInputError(f"invalid postfix token: {token!r}") from exc
                continue
            if len(stack) < 2:
                raise InvalidInputError("invalid postfix expression")
            right, left = stack.pop(), stack.pop()
            if token == "+":
                stack.append(left + right)
            elif token == "-":
                stack.append(left - right)
            elif token == "*":
                stack.append(left * right)
            elif right == 0:
                raise InvalidInputError("division by zero in postfix expression")
            else:
                stack.append(left / right)
        if len(stack) != 1:
            raise InvalidInputError("invalid postfix expression")
        return stack[0]

    @staticmethod
    def next_greater(values: Sequence[int]) -> list[int]:
        """Monotonic stack; -1 where no greater element follows."""
        result = [-1] * len(values)
        stack: list[int] = []
        for index, value in enumerate(values):
            while stack and values[stack[-1]] < value:
                result[stack.pop()] = value
            stack.append(index)
        return result


class QueueAlgorithms:
    @staticmethod
    def generate_binary_numbers(count: int) -> list[str]:
        if count < 0:
            raise InvalidInputError("count must be non-negative")
        queue = deque(["1"])
        result: list[str] = []
        for _ in range(count):
            current = queue.popleft()
            result.append(current)
            queue.extend((current + "0", current + "1"))
        return result

    @staticmethod
    def sliding_window_maximum(values: Sequence[int], window: int) -> list[int]:
        """Monotonic deque, O(n)."""
        if window <= 0 or window > len(values):
            raise InvalidInputError("invalid window")
        indexes: deque[int] = deque()
        result: list[int] = []
        for i, value in enumerate(values):
            while indexes and indexes[0] <= i - window:
                indexes.popleft()
            while indexes and values[indexes[-1]] <= value:
                indexes.pop()
            indexes.append(i)
            if i >= window - 1:
                result.append(values[indexes[0]])
        return result
