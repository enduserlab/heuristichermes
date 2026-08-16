# Installation Guide

## Prerequisites

- Python 3.10 or later
- [Obsidian](https://obsidian.md/) (free download)
- An API key for one supported provider: MiniMax, Anthropic, OpenAI, or xAI

## 1. Clone the repository

```bash
git clone https://github.com/enduserlab/heuristichermes.git
cd heuristichermes
```

## 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

Or, in a virtual environment (recommended):

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Configure your API key

```bash
cp .env.example .env
```

Edit `.env` and set the provider plus the matching API key. If you do not set a provider, Hermes defaults to MiniMax:

```
HERMES_PROVIDER=minimax
MINIMAX_API_KEY=your_key_here
```

All other values have sensible defaults. See `.env.example` for details.

## 4. Initialise a vault

```bash
python scripts/hermes.py init "$HOME/Documents/MyKnowledgeVault"
```

The command prints a JSON plan and its SHA-256. Review it, copy the SHA-256, then apply:

```bash
python scripts/hermes.py init "$HOME/Documents/MyKnowledgeVault" \
  --apply --approved-plan-sha256 <sha256-from-the-plan>
```

## 5. Open the vault in Obsidian

Launch Obsidian → **Open folder as vault** → select the vault directory.

## 6. Adopt an existing vault

If you already have an Obsidian vault, you can adopt it:

```bash
python scripts/hermes.py init /path/to/existing/vault
```

Review the plan. Only **missing** directories and files will be created. Existing content is never overwritten.

## 7. Verify installation

```bash
python scripts/hermes.py lint "$HOME/Documents/MyKnowledgeVault"
```

A freshly initialised vault will report no issues.

## Upgrading

Pull the latest changes and re-run `pip install -r requirements.txt` to get new dependencies.

```bash
git pull
pip install -r requirements.txt
```

## Windows and WSL

heuristichermes works on Windows via [WSL 2](https://learn.microsoft.com/en-us/windows/wsl/install). After installing WSL and Python, follow the Linux instructions above. Vault paths use Unix-style paths inside WSL (e.g. `/mnt/c/Users/yourname/Documents/vault`).

Native Windows (PowerShell/CMD) is supported; use `python` instead of `python3` and replace `$HOME` with `%USERPROFILE%`.
