# Skill: init

**Purpose:** Initialise a new Obsidian vault or adopt an existing directory as a heuristichermes vault.

## Trigger

```
python scripts/hermes.py init <vault_path>
python scripts/hermes.py init <vault_path> --apply --approved-plan-sha256 <sha256>
```

## Contract

1. Without `--apply`, the command prints a JSON plan and its SHA-256. No files are written.
2. With `--apply` and a matching `--approved-plan-sha256`, the plan is executed exactly.
3. If the SHA-256 does not match the current plan, the command exits with an error. No partial writes occur.

## Directories created

| Directory | Purpose |
|-----------|---------|
| `inbox/` | Drop source files here for ingestion |
| `notes/` | Synthesised, linked knowledge pages |
| `sources/` | Immutable, content-addressed source copies |
| `claims/` | Claim-level provenance ledger |
| `indexes/` | Maps of Content and topic indexes |
| `canvas/` | Obsidian Canvas visual maps |
| `logs/` | Operation log (JSONL) |
| `.obsidian/` | Obsidian workspace settings |

## Files created

| File | Purpose |
|------|---------|
| `.hermes.json` | Vault configuration |
| `.obsidian/app.json` | Obsidian app settings |
| `notes/README.md` | Vault orientation note |

## Idempotency

Re-running `init` on an existing vault only creates missing directories and files. Existing content is never overwritten.
