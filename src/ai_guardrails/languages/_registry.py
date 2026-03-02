"""Plugin registry — discovers core and user-provided language plugins.

Core plugins are always registered. Custom plugins are loaded dynamically
from ~/.ai-guardrails/plugins/*.py (or a specified custom_dir).
"""

from __future__ import annotations

import importlib.util
import inspect
import logging
from pathlib import Path

from ai_guardrails.languages._base import BaseLanguagePlugin, LanguagePlugin
from ai_guardrails.languages.cpp import CppPlugin
from ai_guardrails.languages.dotnet import DotnetPlugin
from ai_guardrails.languages.go import GoPlugin
from ai_guardrails.languages.lua import LuaPlugin
from ai_guardrails.languages.node import NodePlugin
from ai_guardrails.languages.python import PythonPlugin
from ai_guardrails.languages.rust import RustPlugin
from ai_guardrails.languages.shell import ShellPlugin
from ai_guardrails.languages.universal import UniversalPlugin

_log = logging.getLogger(__name__)

_CORE_PLUGINS: list[type[BaseLanguagePlugin]] = [
    UniversalPlugin,  # always first — always active
    PythonPlugin,
    NodePlugin,
    RustPlugin,
    GoPlugin,
    DotnetPlugin,
    CppPlugin,
    LuaPlugin,
    ShellPlugin,
]


def _load_custom_plugins(custom_dir: Path, data_dir: Path) -> list[LanguagePlugin]:
    """Dynamically load BaseLanguagePlugin subclasses from custom_dir/*.py."""
    plugins: list[LanguagePlugin] = []
    for py_file in sorted(custom_dir.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001
            _log.warning("Failed to load custom plugin %s", py_file, exc_info=True)
            continue
        for _name, obj in inspect.getmembers(module, inspect.isclass):
            if (
                obj is not BaseLanguagePlugin
                and issubclass(obj, BaseLanguagePlugin)
                and obj.__module__ == module.__name__
            ):
                try:
                    plugin = obj(data_dir)
                    if isinstance(plugin, LanguagePlugin):
                        plugins.append(plugin)
                except Exception:  # noqa: BLE001
                    _log.warning("Failed to instantiate plugin %s", obj, exc_info=True)
    return plugins


def discover_plugins(
    data_dir: Path,
    custom_dir: Path | None = None,
) -> list[LanguagePlugin]:
    """Return all plugin instances: core plugins + any user plugins from custom_dir."""
    plugins: list[LanguagePlugin] = [cls(data_dir) for cls in _CORE_PLUGINS]

    if custom_dir is not None and custom_dir.is_dir():
        plugins.extend(_load_custom_plugins(custom_dir, data_dir))

    return plugins
