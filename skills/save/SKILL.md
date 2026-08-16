# Skill: save

**Purpose:** Save one scoped answer, insight, or observation as a new Obsidian note.

## Trigger

```
python scripts/hermes.py save [vault_path] "<insight>" [--title "<title>"]
```

## Contract

1. The provided insight is formatted into a short, well-structured Markdown note by Hermes.
2. The note includes YAML frontmatter (`title`, `tags`, `created`) and `[[wikilinks]]` to related concepts.
3. One note is created per invocation. Bulk transcript capture is out of scope.
4. The note is written to `notes/` and named after its title slug.
5. The operation is appended to `logs/operations.jsonl`.

## Design rationale

`save` is deliberately scoped to a single insight. This enforces the atomic-note principle and prevents the vault from accumulating unprocessed transcripts. For source material, use `ingest` instead.
