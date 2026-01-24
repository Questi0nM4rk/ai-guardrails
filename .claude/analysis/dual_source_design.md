# Dual Source CodeRabbit Parser Design

## Data Sources

### Source 1: Review Thread Comments (GraphQL) - PRIMARY

**Primary source** - inline comments on specific code lines with full context.

```json
{
  "threads": [
    {
      "path": "src/main.py",
      "line": 42,
      "startLine": 40,
      "body": "_🟠 Major_\n\n**Title**\n\nDescription...<AI prompt>..."
    }
  ]
}
```

| Field | Format | Notes |
|-------|--------|-------|
| path | string | File path |
| line | int | End line of comment range |
| startLine | int\|null | Start line (optional) |
| body | string | Full comment with severity, title, description, **AI prompt** |

**Extracts from thread body:**

- Severity: From first-line emoji/text (🟠 Major, 🟡 Minor, default=suggestion)
- Title: Bold text `**Title**`
- AI prompt: From `<details><summary>🤖 Prompt for AI Agents</summary>` block
- Description: Text between title and details blocks

---

### Source 2: Review Body Summaries - SUPPLEMENTARY

**Supplementary source** - aggregated sections for items not in thread comments.

```html
<summary>🧹 Nitpick comments (N)</summary><blockquote>
  <details>
  <summary>FILENAME (count)</summary><blockquote>
    `LINE-RANGE`: **TITLE**
    DESCRIPTION
  </blockquote></details>
</blockquote></details>
```

| Section | Emoji | Default Severity | Parsed? |
|---------|-------|------------------|---------|
| Nitpick comments | 🧹 | suggestion | ✅ Yes |
| Outside diff range comments | ⚠️ | minor | ✅ Yes |
| Fix all issues with AI agents | 🤖 | major | ❌ No (redundant) |

**Why 🤖 section is NOT parsed:**

The 🤖 body section contains the same AI prompts that are already in thread comments.
Thread comments have richer context (exact file, line, severity, full description),
so parsing the body section would be redundant. AI prompts are extracted from
thread comment bodies via `extract_ai_prompt()`.

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
    source: TaskSource           # thread, nitpick, outside_diff
    start_line: int | None = None
    line_range: str | None = None  # Original "133-134" format from body
    ai_prompt: str | None = None   # Extracted from thread body
    description: str | None = None

class TaskSource(Enum):
    THREAD = "thread"            # From GraphQL reviewThreads (includes AI prompts)
    NITPICK = "nitpick"          # From 🧹 section
    OUTSIDE_DIFF = "outside_diff" # From ⚠️ section
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

1. Thread comment (has full context, AI prompt, inline on code)
2. Outside diff (more specific than nitpick)
3. Nitpick (least specific)

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
    "by_source": {"thread": 4, "nitpick": 3, "outside_diff": 2}
  }
}
```

---

## Parsing Strategy

1. **Parse thread comments** (GraphQL reviewThreads)
   - Extract severity, title, description, AI prompt from each thread body
   - These are the primary tasks with full context

2. **Parse body summaries** (🧹 and ⚠️ sections only)
   - Strip blockquote prefixes (handle `>` lines)
   - Find sections by emoji markers
   - Extract file blocks within each section
   - Parse items with pattern: `` `LINE-RANGE`: **TITLE** ``

3. **Merge and deduplicate**
   - Thread comments take priority
   - Assign sequential IDs to final list
