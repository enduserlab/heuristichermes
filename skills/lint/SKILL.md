# Skill: lint

**Purpose:** Report vault health issues: dead links, orphan notes, frontmatter gaps, and empty sections.

## Trigger

```
python scripts/hermes.py lint [vault_path]
```

## Checks performed

| Check | Severity |
|-------|----------|
| Missing YAML frontmatter | WARN |
| Frontmatter missing `title`, `tags`, or `created` | WARN |
| Dead `[[wikilink]]` (target note does not exist) | ERROR |
| Note body appears empty (only headings/frontmatter) | WARN |
| Orphan note (no incoming wikilinks, excluding README) | INFO |

## Contract

1. The vault is never written to. Lint is a read-only diagnostic.
2. Issues are printed to stdout with severity prefix.
3. The total issue count is logged to `logs/operations.jsonl`.
4. Exit code 0 regardless of issue count (informational output only).
