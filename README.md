# heuristichermes

**Build an Obsidian knowledge base that becomes more useful every time you use it—powered by Hermes through pluggable MiniMax, Anthropic, OpenAI, or xAI providers.**

Capture sources, create connected notes, retrieve grounded answers, and keep the vault healthy—without giving up ownership of your files.

[![MIT license](https://img.shields.io/badge/license-MIT-2563eb.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![MiniMax API](https://img.shields.io/badge/MiniMax-API-7c3aed)](https://platform.minimax.io/)

[See the workflow](#from-source-to-living-knowledge) · [Quick start](#quick-start) · [Explore the skills](#skills) · [Installation guide](docs/install-guide.md)

heuristichermes is a local-first knowledge system for the [Hermes](https://huggingface.co/NousResearch) family of workflows served through pluggable LLM providers including [MiniMax](https://platform.minimax.io/), Anthropic Claude, OpenAI GPT/Codex-compatible models, and xAI Grok. It turns source material into linked, source-cited Obsidian pages; answers from the evidence already in the vault; and provides explicit workflows for research, retrieval, maintenance, and visual mapping.

Your vault remains a normal directory of Markdown files. Nothing is hidden in a plugin cache, locked in a cloud database, or silently uploaded to a model.

## From source to living knowledge

Most AI note workflows stop after saving text. heuristichermes is organised around a repeatable loop: retain the source, ground the claims, connect the knowledge, then put it back to work.

- **Capture with context.** Bring local sources through a visible inbox and preserve immutable, content-addressed copies before synthesis.
- **Ground every important claim.** Source and claim ledgers retain authority, freshness, support, contradiction, confidence, and review state.
- **Connect what you learn.** Build linked pages, indexes, Maps of Content, and Obsidian Canvas views.
- **Use the vault again.** Query, research, retrieve, lint, and fold what is already known instead of starting every conversation from zero.

The output is meant to remain useful with or without an agent: plain Markdown for portability, Obsidian for navigation and visual exploration.

**Design principles:**

- **Local by default.** The vault is user-owned and works as ordinary files. Network egress is a separate, explicit decision.
- **Sources survive the summary.** Notes point back to durable source evidence; unsupported and contradictory claims remain visible.
- **Knowledge compounds deliberately.** Ingestion, querying, linting, retrieval, research, and rollups share one provenance-aware model.
- **Parallel agents cannot race the vault.** Workers return drafts. One orchestrator inspects and applies one recoverable transaction.

This is not an automatic transcript recorder, a cloud sync service, a factual oracle, or a substitute for backups and source control.

## Quick start

### 1. Install prerequisites

```bash
git clone https://github.com/enduserlab/heuristichermes.git
cd heuristichermes
pip install -r requirements.txt
```

Copy `.env.example` to `.env`, then add the API key for your chosen provider. If you do not specify a provider, Hermes defaults to MiniMax:

```bash
cp .env.example .env
# edit .env and set HERMES_PROVIDER plus the matching API key
```

### 2. Initialise a vault

```bash
python scripts/hermes.py init "$HOME/Documents/MyKnowledgeVault"
```

The command prints a JSON plan and its SHA-256. Review it, then apply:

```bash
python scripts/hermes.py init "$HOME/Documents/MyKnowledgeVault" \
  --approved-plan-sha256 "<sha256-from-the-plan>" --apply
```

Open the new directory in Obsidian.

### 3. Ingest a source

Drop a Markdown, plain-text, or PDF file into `inbox/` inside the vault, then run:

```bash
python scripts/hermes.py ingest "$HOME/Documents/MyKnowledgeVault"
```

### 4. Query the vault

```bash
python scripts/hermes.py query "$HOME/Documents/MyKnowledgeVault" \
  "What do my notes say about retrieval-augmented generation?"
```

### 5. Lint the vault

```bash
python scripts/hermes.py lint "$HOME/Documents/MyKnowledgeVault"
```

## Skills

| Skill | What it does |
|-------|--------------|
| `init` | Initialises or adopts a vault |
| `ingest` | Turns captured sources into linked pages and provenance records |
| `query` | Answers read-only from relevant vault evidence |
| `save` | Saves one scoped answer or insight—never an automatic transcript |
| `lint` | Reports dead links, orphans, metadata gaps, stale indexes, and empty sections |
| `retrieve` | Contextual BM25 retrieval with optional cosine reranking |
| `fold` | Extractive, traceable rollups of the operation log |
| `think` | A structured observe–listen–connect–create–grow review loop |

Full skill contracts live in each `skills/<name>/SKILL.md`.

## Configuration

The vault configuration is stored in `.hermes.json` at the vault root. See `config/defaults.json` for all available options and their defaults, including `llm.default_provider` and provider-specific model/base URL settings under `llm.providers`.

Environment variables (or `.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_PROVIDER` | `minimax` | Default LLM provider (`minimax`, `anthropic`, `openai`, or `xai`) |
| `HERMES_MODEL` | Provider-specific config default | Optional model override for the selected provider |
| `MINIMAX_API_KEY` | *(required for MiniMax)* | Your MiniMax API key |
| `ANTHROPIC_API_KEY` | *(required for Anthropic)* | Your Anthropic API key |
| `OPENAI_API_KEY` | *(required for OpenAI)* | Your OpenAI API key |
| `XAI_API_KEY` | *(required for xAI)* | Your xAI API key |
| `MINIMAX_BASE_URL` | `https://api.minimax.io/v1` | Optional MiniMax-compatible API base URL |
| `ANTHROPIC_BASE_URL` | `https://api.anthropic.com/v1` | Optional Anthropic API base URL |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | Optional OpenAI API base URL |
| `XAI_BASE_URL` | `https://api.x.ai/v1` | Optional xAI API base URL |
| `HERMES_VAULT` | *(unset)* | Absolute path to the default vault |

## Architecture

```
heuristichermes/
├── scripts/
│   ├── hermes.py          # CLI entry point
│   └── providers.py       # Provider-agnostic LLM request layer
├── skills/
│   ├── init/SKILL.md
│   ├── ingest/SKILL.md
│   ├── query/SKILL.md
│   ├── save/SKILL.md
│   ├── lint/SKILL.md
│   ├── retrieve/SKILL.md
│   ├── fold/SKILL.md
│   └── think/SKILL.md
├── config/
│   └── defaults.json      # Default vault settings
├── docs/
│   ├── install-guide.md
│   └── quickstart.md
├── .env.example
└── requirements.txt
```

## Vault layout

After initialisation the vault directory looks like:

```
MyKnowledgeVault/
├── .hermes.json           # Vault configuration
├── inbox/                 # Drop sources here for ingestion
├── notes/                 # Synthesised, linked knowledge pages
├── sources/               # Immutable, content-addressed source copies
├── claims/                # Claim-level provenance ledger
├── indexes/               # Maps of Content and topic indexes
├── canvas/                # Obsidian Canvas files
├── logs/                  # Operation log (JSONL)
└── .obsidian/             # Obsidian workspace settings
```

## Contributing

Pull requests are welcome. Please open an issue first to discuss what you would like to change.

## Licence

[MIT](LICENSE)