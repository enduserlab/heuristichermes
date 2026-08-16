# Skill: query

**Purpose:** Answer a question using only the evidence already in the vault (read-only).

## Trigger

```
python scripts/hermes.py query [vault_path] "<question>"
```

## Contract

1. The command retrieves the most relevant notes using BM25 keyword scoring.
2. The top-K notes (default: 10, configurable in `.hermes.json`) are passed as context.
3. The Hermes model answers using only the provided vault evidence.
4. Claims not supported by the evidence are explicitly flagged.
5. Vault note titles are cited as `[[wikilinks]]` in the answer.
6. The vault is never written to. The query is logged to `logs/operations.jsonl`.

## Limitations

- Retrieval is keyword-based (BM25). Semantic/cosine reranking is available but optional (see `retrieve` skill).
- Context is capped at 2000 characters per note to stay within model limits.
- The model will not invent facts not present in the retrieved notes.
