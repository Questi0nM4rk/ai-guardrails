# Scaffold a new pipeline step

Create a new step for the v1 pipeline (src/ai_guardrails/steps/).

## Arguments

$ARGUMENTS = step name in snake_case (e.g., `validate_configs`)

## Steps

1. Create `src/ai_guardrails/steps/$ARGUMENTS.py`:
   - `from __future__ import annotations` — first line
   - Subclass `BaseLanguagePlugin` — no, steps are standalone classes
   - Class with `name`, `validate(ctx)`, `execute(ctx)` following the `PipelineStep` Protocol
   - See `src/ai_guardrails/steps/setup_hooks.py` for a minimal example
   - Max 200 lines

2. Export from `src/ai_guardrails/steps/__init__.py`:
   - Add import and `__all__` entry

3. Create `tests/test_v1/steps/test_$ARGUMENTS.py`:
   - `from __future__ import annotations`
   - Import step class
   - Use `FakeCommandRunner`, `FakeFileManager`, `FakeConsole` from `tests/test_v1/conftest.py`
   - Use `tmp_path` fixture for filesystem operations
   - Required tests:
     - `test_{step_name}_step_name` — name attribute
     - `test_{step_name}_happy_path` — successful execute()
     - `test_{step_name}_failure_case` — specific failure handled
     - `test_{step_name}_validate_returns_empty` — if validate() has no preconditions

4. Wire into the appropriate pipeline in `src/ai_guardrails/pipelines/`:
   - Import and append to steps list at the correct position

5. Run: `uv run pytest tests/test_v1/steps/test_$ARGUMENTS.py -v`

6. Run full suite: `uv run pytest tests/test_v1/ -v`
