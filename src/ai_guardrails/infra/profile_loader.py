"""ProfileLoader — resolve Profile instances from named TOML profile files."""

from __future__ import annotations

import dataclasses
from pathlib import Path
import tomllib
from typing import Any

from ai_guardrails.models.profile import Profile

_PROFILES_DIR = Path(__file__).parent.parent / "_data" / "profiles"
_MAX_DEPTH = 10


def load_profile(name: str, *, profiles_dir: Path | None = None) -> Profile:
    """Load and fully resolve a named profile, following the inheritance chain.

    Args:
        name: Profile name (e.g. "strict", "standard", "minimal").
        profiles_dir: Override the default profiles directory (for testing).

    Raises:
        ValueError: Unknown profile name or circular inheritance detected.
    """
    return _resolve(name, profiles_dir or _PROFILES_DIR, [])


def _resolve(name: str, dir_: Path, chain: list[str]) -> Profile:
    if name in chain:
        msg = f"Circular profile inheritance: {' → '.join([*chain, name])}"
        raise ValueError(msg)
    if len(chain) >= _MAX_DEPTH:
        msg = f"Profile inheritance chain too deep (>{_MAX_DEPTH}): {chain}"
        raise ValueError(msg)

    path = dir_ / f"{name}.toml"
    if not path.exists():
        available = ", ".join(sorted(p.stem for p in dir_.glob("*.toml")))
        msg = f"Unknown profile {name!r}. Available: {available}"
        raise ValueError(msg)

    with path.open("rb") as fh:
        data: dict[str, Any] = tomllib.load(fh)
    data.setdefault("name", name)

    parent_name = data.get("inherits")
    if not parent_name:
        return Profile.from_dict(data)

    parent = _resolve(parent_name, dir_, [*chain, name])
    return _merge(parent, data)


def _merge(parent: Profile, child_data: dict[str, Any]) -> Profile:
    """Return a new Profile with parent values overridden by child's explicit fields."""
    merged = dataclasses.asdict(parent)
    for key, value in child_data.items():
        if key != "inherits" and key in merged:
            merged[key] = value
    return Profile.from_dict(merged)
