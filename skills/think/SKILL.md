# Skill: think

**Purpose:** Apply the Observe–Listen–Connect–Create–Grow (OLCCG) review loop to a topic using vault evidence.

## Trigger

```
python scripts/hermes.py think [vault_path] "<topic>"
```

## OLCCG loop

| Phase | What Hermes does |
|-------|-----------------|
| **Observe** | Identifies what the vault notes reveal about the topic |
| **Listen** | Surfaces patterns, tensions, and open questions |
| **Connect** | Suggests wikilinks to existing or new concepts |
| **Create** | Proposes one concrete new note or vault improvement |
| **Grow** | Recommends the next action to compound knowledge |

## Contract

1. The top 5 most relevant notes are retrieved and passed as context.
2. Hermes applies the OLCCG loop and cites evidence with `[[wikilinks]]`.
3. The reflection is printed to stdout in Markdown format.
4. The vault is never written to automatically; the `Create` phase is a proposal only.
5. The operation is logged to `logs/operations.jsonl`.
