# Skill: retrieve

**Purpose:** Return the most relevant notes for a free-text query using BM25 keyword scoring.

## Trigger

```
python scripts/hermes.py retrieve [vault_path] "<query>" [--top-k 10]
```

## Contract

1. Notes in `notes/` are scored against the query using term-frequency counting (BM25 approximation).
2. Results are returned in descending score order, up to `--top-k` results.
3. The vault is never written to.
4. Scores are displayed alongside note paths for transparency.

## Configuration

| Key | Default | Description |
|-----|---------|-------------|
| `retrieve.top_k` | `10` | Default number of results |
| `retrieve.rerank` | `false` | Enable cosine reranking (requires sentence-transformers) |
