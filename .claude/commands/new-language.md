# Add support for a new language

Add full language support: detection, configs, hooks, and tests.

## Arguments

$ARGUMENTS = language name (e.g., `kotlin`, `swift`)

## Steps

1. **Detection**: Add language entry to `configs/languages.yaml`:
   - File extensions for detection
   - Config files to look for (e.g., `build.gradle.kts` for Kotlin)
   - Map to config template paths

2. **Base config**: Add maximally strict config to `configs/`:
   - Enable ALL rules by default
   - Strictest settings available
   - Document which tool this configures

3. **Pre-commit hooks**: Add hook template to `templates/pre-commit/`:
   - Linter hook (check-only)
   - Formatter hook (if applicable)
   - Follow existing template patterns

4. **Format stage**: Add formatter entry to `lib/python/guardrails/hooks/format_stage.py`:
   - Auto-fix command for local pre-commit

5. **Suppression patterns**: Add to `lib/python/guardrails/constants.py`:
   - Language-specific suppression comment patterns to detect and reject

6. **Constants**: Add language config mapping to `lib/python/guardrails/constants.py`:
   - Add to `LANG_CONFIGS` dict

7. **Tests**:
   - Detection test in `tests/test_detection.py` or `tests/test_init_integration.py`
   - Config copy test
   - Hook formatting test
   - Run: `uv run pytest tests/ -v -k "$ARGUMENTS"`

8. Verify: `uv run ruff check lib/python/ && uv run pyright`
