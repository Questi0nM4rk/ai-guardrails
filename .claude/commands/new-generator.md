# Scaffold a new config generator

Create a config generator module that produces tool configuration from the exception registry.

## Arguments

$ARGUMENTS = tool name in snake_case (e.g., `eslint`)

## Steps

1. Read `lib/python/guardrails/generators/ruff.py` as the reference pattern

2. Create `lib/python/guardrails/generators/$ARGUMENTS.py`:
   - `from __future__ import annotations`
   - Single public function: `generate_{tool_name}(registry_path: Path, output_path: Path) -> None`
   - Parse exceptions from registry TOML
   - Merge with base config from `configs/`
   - Write output preserving comments where possible (use tomlkit/ruamel.yaml)

3. Create `tests/test_generator_$ARGUMENTS.py`:
   - Test with empty registry (base config only)
   - Test with exceptions applied
   - Test round-trip: generate -> parse -> validate structure

4. Register in `lib/python/guardrails/generate.py`:
   - Add to the generator dispatch table

5. Run: `uv run pytest tests/test_generator_$ARGUMENTS.py -v`
