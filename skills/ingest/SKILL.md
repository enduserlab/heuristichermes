# Skill: ingest

**Purpose:** Turn source files in the vault inbox into linked, source-cited Obsidian notes.

## Trigger

```
python scripts/hermes.py ingest [vault_path]
```

## Contract

1. All files in `inbox/` with extensions `.md`, `.txt`, or `.pdf` are processed in order.
2. An immutable, content-addressed copy of each source is written to `sources/` before synthesis. The copy name is `<sha256_prefix>-<original_filename>`.
3. The Hermes model (via MiniMax API) synthesises one linked Markdown note per source.
4. The synthesised note is written to `notes/` and named after the note's derived title slug.
5. Processed source files are moved to `inbox/processed/`.
6. Every operation is appended to `logs/operations.jsonl`.

## Note format

Each synthesised note includes:

- YAML frontmatter: `title`, `tags`, `source`, `created`
- Linked concepts as `[[wikilinks]]`
- A `## Sources` section citing the archive filename

## Guarantees

- The source archive is written before synthesis begins.
- If the API call fails, the source file remains in `inbox/` and no partial note is written.
