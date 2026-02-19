# Scaffold a new pipeline step

Create a new pipeline step module and its test file.

## Arguments

$ARGUMENTS = step name in snake_case (e.g., `validate_configs`)

## Steps

1. Create `lib/python/guardrails/steps/$ARGUMENTS.py`:
   - `from __future__ import annotations`
   - Import types: `from pathlib import Path`
   - Single public function: `run_{step_name}(project_dir, *, console, runner)`
   - Signature: `(project_dir: Path, *, console: Console | None = None,
     runner: CommandRunner | None = None) -> None`
   - Use default Console/CommandRunner if not injected
   - Docstring explaining what the step does

2. Create `tests/test_step_$ARGUMENTS.py`:
   - `from __future__ import annotations`
   - Import the step function
   - Import FakeConsole and FakeCommandRunner from conftest
   - Scaffold 3 test functions:
     - `test_{step_name}_basic` — happy path
     - `test_{step_name}_skip_condition` — when step should be skipped
     - `test_{step_name}_error_handling` — specific exception caught

3. Register the step:
   - Add import to `lib/python/guardrails/steps/__init__.py`
   - Add call in the appropriate pipeline orchestrator

4. Run: `uv run pytest tests/test_step_$ARGUMENTS.py -v`
