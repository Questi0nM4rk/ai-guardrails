# Scaffold a new pipeline step

Create a new helper module and its test file for the init pipeline.

## Arguments

$ARGUMENTS = step name in snake_case (e.g., `validate_configs`)

## Steps

1. Create `lib/python/guardrails/$ARGUMENTS.py`:
   - `from __future__ import annotations`
   - Import types: `from pathlib import Path`
   - Single public function with typed signature
   - Follow existing patterns in `init.py` helper functions
   - Docstring explaining what the step does

2. Create `tests/test_$ARGUMENTS.py`:
   - `from __future__ import annotations`
   - Import the step function
   - Use `unittest.mock.patch` for subprocess/IO boundaries
   - Use `tmp_path` fixture for filesystem operations
   - Scaffold 3 test functions:
     - `test_{step_name}_basic` — happy path
     - `test_{step_name}_skip_condition` — when step should be skipped
     - `test_{step_name}_error_handling` — specific exception caught

3. Register the step:
   - Import in the appropriate entry point (e.g., `run_init` in
     `lib/python/guardrails/init.py`)
   - Add the call at the correct point in the pipeline

4. Run: `uv run pytest tests/test_$ARGUMENTS.py -v`
