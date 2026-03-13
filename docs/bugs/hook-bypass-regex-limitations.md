# Hook Bypass — Regex Limitations (Deferred)

**Status**: Deferred — current regex approach will be replaced with a proper
command tokenizer. These are known limitations, not bugs.

---

## 1. `rm -rf file1 file2` bypasses the rm pattern

**File**: `src/hooks/dangerous-patterns.ts`

**Pattern**: The trailing anchor `(?:[^/\s]*\/?\\s*$|\/)` requires either
end-of-line or a `/` after the target. For multi-target commands like
`rm -rf node_modules dist`, `[^/\s]*` matches `node_modules` but `\s*$`
fails because `dist` remains, and `\/` fails because there's no slash.
Result: no match.

**Partially mitigated by** `DANGEROUS_DENY_GLOBS` (`"Bash(rm -rf *)"`) at
the Claude tool-use layer, but the hook regex itself has the gap.

**Fix (future)**: Drop the trailing path anchor, or switch to tokenizer-based
checking where any `rm` with both `-r` and `-f` flags is unconditionally blocked.

---

## 2. `sudo -u root rm -rf /` not blocked by the sudo unwrapper

**File**: `src/hooks/dangerous-patterns.ts`

**Pattern**: The sudo/doas unwrapper uses `args.findIndex` to find the first
non-dash token. For `sudo -u root rm -rf /`, the first non-dash token is
`root` (the argument to `-u`), not `rm`. The unwrapper then checks `rm` as
if it were a flag, missing it entirely.

**Fix (future)**: Maintain a `SUDO_ARG_FLAGS` set (`-u`, `-g`, `-H`, `-C`,
`-r`, etc.) and skip their arguments when scanning for the real command.
Or switch to a proper tokenizer that understands option–argument pairs.

---

## 3. `protect-configs.ts` false positives on cp/mv/cat source reads

**File**: `src/hooks/protect-configs.ts`

**Pattern**: `WRITE_PATTERNS` contains `/\bcp\b/`, `/\bmv\b/`, `/\bcat\s+.*>/`,
`/\becho\b.*>/`, `/\bprintf\b.*>/`. These fire whenever the managed filename
appears anywhere in the command, including when it is the *source*:

- `cp ruff.toml /tmp/backup` → blocked (false positive, managed file is source)
- `cat ruff.toml > /tmp/backup` → blocked (false positive, managed file is read)

`redirectToManaged` already anchors `>>?` to the managed file as the write
target. `cat+>`, `echo+>`, `printf+>` duplicate that check and add false
positives. `cp` and `mv` need destination-anchoring.

**Fix (future)**: Remove `cat+>`, `echo+>`, `printf+>` from `WRITE_PATTERNS`
(redundant). For `cp`/`mv`, anchor to the managed file being the last
(destination) argument. Or replace with a tokenizer.

---

## Why deferred

Both issues stem from the fundamental limitation of regex-based command
parsing. Fixing them with more regex creates fragile, unmaintainable patterns
that will inevitably have new edge cases. The correct fix is to replace the
regex approach with a shell-quote tokenizer that properly handles:

- Multi-target commands
- Flag–argument pairs
- Quoting and escaping
- Pipe/redirect operators

This work is tracked separately. The existing regex provides meaningful
protection against the common cases and the Claude tool-use layer (`DANGEROUS_DENY_GLOBS`)
provides a second line of defense.
