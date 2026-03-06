# Scaffold a new config generator for an existing language plugin

Adds a new generated config file to an existing language plugin in `src/ai_guardrails/languages/`.

## Arguments

$ARGUMENTS = `{language}:{config_filename}` — e.g., `python:pyrightconfig.json` or `node:tsconfig.json`

Parse as: `LANG` = part before `:`, `CONFIG` = part after `:`

## Steps

1. **Locate the language plugin**: `src/ai_guardrails/languages/{LANG}.py`
   - Read the file first — understand existing `generated_configs`, `generate()`, and `check()` methods

2. **Add to `generated_configs` class var**:
   ```python
   generated_configs: ClassVar[list[str]] = [
       ...,
       "{CONFIG}",  # add here
   ]
   ```

3. **Add a private generation helper** following the existing pattern:
   ```python
   def _generate_{slug}(
       self,
       registry: ExceptionRegistry,
       languages: list[str],
       project_dir: Path,
   ) -> str:
       """Return content for {CONFIG}."""
       body = "<generated content here>"
       return f"{make_hash_header(body)}\n{body}"
   ```
   Where `{slug}` = CONFIG filename with non-alphanumeric chars replaced by `_`.

4. **Wire into `generate()`** — add to the returned dict:
   ```python
   Path("{CONFIG}"): self._generate_{slug}(registry, languages, project_dir),
   ```

5. **Add a `check()` entry** using `verify_hash`:
   ```python
   config_path = project_dir / "{CONFIG}"
   if not config_path.exists():
       stale.append("{CONFIG} missing")
   elif not verify_hash(config_path.read_text(), self._generate_{slug}(registry, languages, project_dir).split("\n", 1)[1]):
       stale.append("{CONFIG} stale")
   ```

6. **Add data template** (if config uses a static template):
   - Place at `src/ai_guardrails/_data/templates/{LANG}/{CONFIG}`
   - Load via `importlib.resources` — see existing plugins for the pattern

7. **Write tests** in `tests/test_v1/languages/test_{LANG}.py`:
   - `test_{LANG}_{slug}_generates_with_hash_header`
   - `test_{LANG}_{slug}_check_returns_stale_when_missing`
   - `test_{LANG}_{slug}_check_returns_stale_when_tampered`
   - `test_{LANG}_{slug}_check_returns_fresh_when_current`

8. **Run**:
   ```bash
   uv run pytest tests/test_v1/languages/test_{LANG}.py -v
   uv run pytest tests/test_v1/ -v
   ```

## Key imports

```python
from ai_guardrails.generators.base import make_hash_header, verify_hash
```

## Max 200 lines per file — if the plugin exceeds this, split helpers to `_{LANG}_checks.py`
