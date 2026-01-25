# Bad Python code - should fail ruff and mypy

import os
import sys  # Multiple imports on same line (E401)
from typing import *  # Star import (F403)


# Missing type annotations (ANN001)
def process(data):
    result = []
    for item in data:
        result.append(item * 2)  # Could use list comprehension (C417)
    return result


# Missing docstring (D100, D103)
def calculate(x, y):
    # Unused variable (F841)
    unused = 42
    return x + y


# Missing return type annotation (ANN201)
def get_value(key):
    d = {"a": 1, "b": 2}
    return d.get(key)  # No default, could return None


class User:  # Missing docstring (D101)
    # Missing __init__ type annotations
    def __init__(self, name, age):
        self.name = name
        self.age = age

    # Missing method docstring and type hints
    def greet(self):
        print(f"Hello, {self.name}!")  # T201: print statement


# Unused import at top
_ = os
_ = sys
