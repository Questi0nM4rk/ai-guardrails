"""Good Python code - should pass ruff and mypy strict mode.

This module demonstrates proper Python code style with:
- Type annotations
- Docstrings
- No unused imports
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


def process(data: Sequence[int]) -> list[int]:
    """Process a sequence of integers by doubling each value.

    Args:
        data: A sequence of integers to process.

    Returns:
        A list with each input value doubled.
    """
    return [item * 2 for item in data]


def calculate(x: int, y: int) -> int:
    """Calculate the sum of two integers.

    Args:
        x: First integer.
        y: Second integer.

    Returns:
        The sum of x and y.
    """
    return x + y


def get_value(key: str, default: int = 0) -> int:
    """Get a value from a predefined dictionary.

    Args:
        key: The key to look up.
        default: Value to return if key not found.

    Returns:
        The value associated with the key, or the default.
    """
    data: dict[str, int] = {"a": 1, "b": 2}
    return data.get(key, default)


class User:
    """A simple user class with name and age attributes."""

    def __init__(self, name: str, age: int) -> None:
        """Initialize a User instance.

        Args:
            name: The user's name.
            age: The user's age in years.
        """
        self.name = name
        self.age = age

    def greet(self) -> str:
        """Generate a greeting message for this user.

        Returns:
            A greeting string.
        """
        return f"Hello, {self.name}!"


if __name__ == "__main__":
    user = User("Alice", 30)
    greeting = user.greet()
    # Use the result without print
    _ = greeting
