# Quick Start

Get up and running with heuristichermes in five minutes.

## Before you begin

Ensure you have completed [installation](install-guide.md) and have a vault initialised.

LLM-backed commands such as `ingest`, `query`, `save`, `fold`, and `think` accept optional `--provider` and `--model` overrides. If omitted, Hermes uses `HERMES_PROVIDER` or the vault's configured `llm.default_provider`, which defaults to `minimax`.

## Ingest your first source

1. Copy or write a Markdown or plain-text file into the vault's `inbox/` directory.

   ```
   cp my-article.md "$HOME/Documents/MyKnowledgeVault/inbox/"
   ```

2. Run the ingest command:

   ```bash
   python scripts/hermes.py ingest "$HOME/Documents/MyKnowledgeVault"
   ```

   Hermes will synthesise a linked note and place it in `notes/`. The original file moves to `inbox/processed/`.

## Query the vault

Ask a question about what you've ingested:

```bash
python scripts/hermes.py query "$HOME/Documents/MyKnowledgeVault" \
  "What are the key ideas in my notes?"
```

Or override the provider for one call:

```bash
python scripts/hermes.py query "$HOME/Documents/MyKnowledgeVault" \
  --provider openai \
  "What are the key ideas in my notes?"
```

Hermes answers using only evidence from your vault and cites notes with `[[wikilinks]]`.

## Save a quick insight

Capture a thought without a source file:

```bash
python scripts/hermes.py save "$HOME/Documents/MyKnowledgeVault" \
  "Spaced repetition works because retrieval strengthens memory traces." \
  --title "Spaced repetition and memory"
```

## Lint the vault

Check for dead links, orphan notes, and missing frontmatter:

```bash
python scripts/hermes.py lint "$HOME/Documents/MyKnowledgeVault"
```

## Reflect on a topic

Use the Observe–Listen–Connect–Create–Grow loop:

```bash
python scripts/hermes.py think "$HOME/Documents/MyKnowledgeVault" \
  "retrieval-augmented generation"
```

## Retrieve relevant notes

Find the notes most relevant to a topic without invoking the LLM:

```bash
python scripts/hermes.py retrieve "$HOME/Documents/MyKnowledgeVault" \
  "knowledge management" --top-k 5
```

## Review activity

Summarise recent vault operations:

```bash
python scripts/hermes.py fold "$HOME/Documents/MyKnowledgeVault"
```

## Next steps

- Open the vault in Obsidian to explore the Graph view and Canvas files.
- Customise `.hermes.json` to change the default provider, model, retrieval depth, or directory layout.
- See each `skills/<name>/SKILL.md` for the full contract of each command.
