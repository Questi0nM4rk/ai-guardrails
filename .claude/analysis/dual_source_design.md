# Dual Source CodeRabbit Parser Design

## Data Sources

### Source 1: Review Thread Comments (GraphQL)

**Current implementation** - inline comments on specific lines.

```json
{
  "threads": [
    {
      "path": "src/main.py",
      "line": 42,
      "startLine": 40,
      "body": "_🟠 Major_\n\n**Title**\n\nDescription..."
    }
  ]
}
```

| Field | Format | Notes |
|-------|--------|-------|
| path | string | File path |
| line | int | End line of comment range |
| startLine | int\|null | Start line (optional) |
| body | string | Full comment with severity, title, description |

**Severity extraction:** From first line emoji/text (🟠 Major, 🟡 Minor, default=suggestion)

---

## Source 2: Review Body Summaries

**Need to add** - aggregated sections in review body.

```html
<summary>🧹 Nitpick comments (N)</summary><blockquote>
  <details>
  <summary>FILENAME (count)</summary><blockquote>
    `LINE-RANGE`: **TITLE**
    DESCRIPTION
    [optional: <details><summary>📝 Suggested fix</summary>...</details>]
  </blockquote></details>
</blockquote></details>
```

| Section | Emoji | Default Severity |
|---------|-------|------------------|
| Nitpick comments | 🧹 | suggestion |
| Outside diff range comments | ⚠️ | minor |
| Fix all issues with AI agents | 🤖 | major |

**Format differences:**

- Line range: String `"133-134"` vs integers
- May have `>` blockquote prefixes (need stripping)
- Nested: section → file → comments

---

## Key Differences

| Aspect | Thread Comments | Body Summaries |
|--------|-----------------|----------------|
| Line format | `line: 42, startLine: 40` | `"133-134"` string |
| Severity | In body text | From section type |
| Structure | Flat list | Nested (section→file→item) |
| Blockquotes | No | Yes (⚠️ section) |
| AI prompt | In body | In 🤖 section |

---

## Unified Task Model

```python
@dataclass
class Task:
    id: str
    file: str
    line: int                    # End line (primary)
    title: str
    severity: Severity
    source: TaskSource           # NEW: thread, nitpick, outside_diff, ai_prompt
    start_line: int | None = None
    line_range: str | None = None  # NEW: Original "133-134" format
    ai_prompt: str | None = None
    description: str | None = None

class TaskSource(Enum):
    THREAD = "thread"            # From GraphQL reviewThreads
    NITPICK = "nitpick"          # From 🧹 section
    OUTSIDE_DIFF = "outside_diff" # From ⚠️ section
    AI_PROMPT = "ai_prompt"      # From 🤖 section
```

---

## Deduplication Strategy

**Key:** `(file, line_start, normalize(title))`

```python
def dedup_key(task: Task) -> tuple:
    line_start = task.start_line or task.line
    title_norm = task.title.lower().strip()[:50]
    return (task.file, line_start, title_norm)
```

**Priority:** If duplicate found, prefer:

1. Thread comment (has more context, inline on code)
2. Outside diff (more specific than nitpick)
3. Nitpick
4. AI prompt (least specific)

---

## Input/Output Schema

### Input (from shell script)

```json
{
  "threads": [],
  "review_bodies": []
}
```

### Output

```json
{
  "tasks": [],
  "summary": {
    "total": 10,
    "by_severity": {"major": 2, "minor": 3, "suggestion": 5},
    "by_file": {"src/main.py": 3, "README.md": 2},
    "by_source": {"thread": 4, "nitpick": 3, "outside_diff": 2, "ai_prompt": 1}
  }
}
```

---

## Parsing Strategy

1. **Strip blockquote prefixes** from body (handle `>` lines)
2. **Find sections** by emoji markers (🧹, ⚠️, 🤖)
3. **Extract file blocks** within each section
4. **Parse items** with pattern: `` `LINE-RANGE`: **TITLE** ``
5. **Convert line range** "40-50" → start_line=40, line=50
6. **Merge with threads** using dedup key
7. **Assign IDs** to final merged list
