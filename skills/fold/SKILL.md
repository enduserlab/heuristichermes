# Skill: fold

**Purpose:** Produce an extractive, traceable rollup of the vault operation log.

## Trigger

```
python scripts/hermes.py fold [vault_path]
```

## Contract

1. The last 200 records from `logs/operations.jsonl` are summarised by Hermes.
2. The rollup includes: operation counts by type, date range, notable activity, and anomalies.
3. The summary is printed to stdout in Markdown format.
4. The vault is never written to during a fold.

## Use cases

- Weekly review of vault activity
- Auditing what was ingested, queried, or saved
- Identifying stale or unused workflows
