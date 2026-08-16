#!/usr/bin/env python3
"""
hermes.py – heuristichermes CLI

Local-first Obsidian knowledge system powered by Hermes-compatible LLM
providers. Vault operations: init, ingest, query, save, lint, retrieve, fold,
think.

Usage:
    python scripts/hermes.py init <vault_path> [--apply --approved-plan-sha256 <sha>]
    python scripts/hermes.py ingest <vault_path>
    python scripts/hermes.py query  <vault_path> "<question>"
    python scripts/hermes.py save   <vault_path> "<insight>" [--title <title>]
    python scripts/hermes.py lint   <vault_path>
    python scripts/hermes.py retrieve <vault_path> "<query>" [--top-k 10]
    python scripts/hermes.py fold   <vault_path>
    python scripts/hermes.py think  <vault_path> "<topic>"
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import textwrap
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

if __package__ in {None, ""}:  # pragma: no cover - script execution path
    providers_path = Path(__file__).resolve().with_name("providers.py")
    providers_spec = importlib.util.spec_from_file_location(
        "hermes_providers",
        providers_path,
    )
    if providers_spec is None or providers_spec.loader is None:
        raise ImportError(f"Unable to load provider module from {providers_path}")
    providers_module = importlib.util.module_from_spec(providers_spec)
    providers_spec.loader.exec_module(providers_module)
    SUPPORTED_PROVIDERS = providers_module.SUPPORTED_PROVIDERS
    generate_response = providers_module.generate_response
    resolve_llm_settings = providers_module.resolve_llm_settings
else:
    from .providers import SUPPORTED_PROVIDERS, generate_response, resolve_llm_settings

load_dotenv()

console = Console()

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "defaults.json"
VAULT_CONFIG_FILE = ".hermes.json"
VAULT_LOG_FILE = "logs/operations.jsonl"
INGEST_EXTENSIONS = {".md", ".txt", ".pdf"}


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------


def load_defaults() -> dict[str, Any]:
    with DEFAULT_CONFIG_PATH.open() as fh:
        return _normalise_config(json.load(fh))


def load_vault_config(vault: Path) -> dict[str, Any]:
    cfg_path = vault / VAULT_CONFIG_FILE
    defaults = load_defaults()
    if cfg_path.exists():
        with cfg_path.open() as fh:
            overrides = json.load(fh)
        defaults = _deep_merge(defaults, overrides)
    return _normalise_config(defaults)


def save_vault_config(vault: Path, cfg: dict[str, Any]) -> None:
    cfg_path = vault / VAULT_CONFIG_FILE
    with cfg_path.open("w") as fh:
        json.dump(cfg, fh, indent=2)


def _deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _normalise_config(cfg: dict[str, Any]) -> dict[str, Any]:
    normalised = deepcopy(cfg)
    llm_cfg = normalised.setdefault("llm", {})
    default_provider = (
        llm_cfg.get("default_provider")
        or normalised.get("provider")
        or "minimax"
    )
    llm_cfg["default_provider"] = str(default_provider).lower()
    provider_map = llm_cfg.setdefault("providers", {})
    legacy_model = normalised.get("model")
    if legacy_model:
        legacy_provider = llm_cfg["default_provider"]
        provider_map.setdefault(legacy_provider, {})
        provider_map[legacy_provider]["model"] = legacy_model
    return normalised


def _llm_option_defaults_help() -> str:
    return "Defaults to environment variables or the vault config."


def _llm_options(func: Any) -> Any:
    func = click.option(
        "--model",
        "model_override",
        default=None,
        help=f"Override the configured model. {_llm_option_defaults_help()}",
    )(func)
    func = click.option(
        "--provider",
        "provider_override",
        type=click.Choice(SUPPORTED_PROVIDERS, case_sensitive=False),
        default=None,
        help=f"Override the configured provider. {_llm_option_defaults_help()}",
    )(func)
    return func


def _chat_completion(
    cfg: dict[str, Any],
    *,
    prompt: str,
    system_prompt: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.3,
    provider_override: str | None = None,
    model_override: str | None = None,
) -> str:
    llm_settings = resolve_llm_settings(
        cfg,
        provider=provider_override,
        model=model_override,
    )
    return generate_response(
        provider=llm_settings["provider"],
        model=llm_settings["model"],
        prompt=prompt,
        system_prompt=system_prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        base_url=llm_settings["base_url"],
    )


# ---------------------------------------------------------------------------
# Vault helpers
# ---------------------------------------------------------------------------


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log_operation(vault: Path, record: dict[str, Any]) -> None:
    log_path = vault / VAULT_LOG_FILE
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a") as fh:
        fh.write(json.dumps(record) + "\n")


def _select_vault(vault_arg: str | None) -> Path:
    if vault_arg:
        return Path(vault_arg).expanduser().resolve()
    env_vault = os.environ.get("HERMES_VAULT", "")
    if env_vault:
        return Path(env_vault).expanduser().resolve()
    # Walk upward looking for a .hermes.json
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / VAULT_CONFIG_FILE).exists():
            return parent
    raise click.UsageError(
        "Cannot determine vault path.  Pass a path argument, "
        "set HERMES_VAULT, or run from inside an initialised vault."
    )


def _require_vault(vault_path: Path) -> None:
    if not (vault_path / VAULT_CONFIG_FILE).exists():
        raise click.UsageError(
            f"{vault_path} does not look like an initialised vault "
            f"(missing {VAULT_CONFIG_FILE}).  Run `init` first."
        )


def _build_inbox_index(vault: Path, cfg: dict[str, Any]) -> list[Path]:
    inbox = vault / cfg["inbox_dir"]
    if not inbox.exists():
        return []
    return [
        p
        for p in inbox.iterdir()
        if p.is_file() and p.suffix.lower() in INGEST_EXTENSIONS
    ]


def _read_source(path: Path) -> str:
    """Return text content of a source file (plain text or Markdown)."""
    if path.suffix.lower() == ".pdf":
        # Basic: read raw bytes and decode what we can
        # A real implementation would use pdfminer or pypdf
        return path.read_bytes().decode("latin-1", errors="replace")
    return path.read_text(encoding="utf-8", errors="replace")


def _note_slug(title: str) -> str:
    """Return a filesystem-safe slug for a note title."""
    import re
    slug = re.sub(r"[^a-zA-Z0-9 _-]", "", title).strip().replace(" ", "-").lower()
    return slug[:80] or "note"


def _wikilink(title: str) -> str:
    return f"[[{title}]]"


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------

VAULT_DIRS = [
    "inbox",
    "notes",
    "sources",
    "claims",
    "indexes",
    "canvas",
    "logs",
    ".obsidian",
]

OBSIDIAN_APP_JSON = json.dumps(
    {
        "legacyEditor": False,
        "livePreview": True,
        "defaultViewMode": "source",
        "promptDelete": True,
        "newLinkFormat": "shortest",
        "useMarkdownLinks": False,
    },
    indent=2,
)


def _plan_init(vault: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    dirs_to_create = [str(vault / d) for d in VAULT_DIRS if not (vault / d).exists()]
    files_to_create: list[dict[str, str]] = []
    cfg_path = vault / VAULT_CONFIG_FILE
    if not cfg_path.exists():
        files_to_create.append({"path": str(cfg_path), "content": json.dumps(cfg, indent=2)})
    obs_app = vault / ".obsidian" / "app.json"
    if not obs_app.exists():
        files_to_create.append({"path": str(obs_app), "content": OBSIDIAN_APP_JSON})
    readme_path = vault / "notes" / "README.md"
    if not readme_path.exists():
        readme_content = textwrap.dedent(f"""\
            ---
            title: Knowledge Vault
            tags: [index, vault]
            created: {_now_iso()}
            ---

            # Knowledge Vault

            Initialised by heuristichermes on {_now_iso()}.

            ## Structure

            - **inbox/** – drop source files here for ingestion
            - **notes/** – synthesised knowledge pages (this directory)
            - **sources/** – immutable content-addressed source copies
            - **claims/** – claim-level provenance ledger
            - **indexes/** – Maps of Content and topic indexes
            - **canvas/** – Obsidian Canvas visual maps
            - **logs/** – operation log (JSONL)

            Run `python scripts/hermes.py ingest <vault>` to process inbox files.
        """)
        files_to_create.append({"path": str(readme_path), "content": readme_content})
    plan = {
        "operation": "init",
        "vault": str(vault),
        "dirs_to_create": dirs_to_create,
        "files_to_create": [f["path"] for f in files_to_create],
        "generated_at": _now_iso(),
        "_files": files_to_create,
    }
    serialisable = {k: v for k, v in plan.items() if not k.startswith("_")}
    # Exclude generated_at from the SHA so plan and apply calls produce the same hash.
    stable = {k: v for k, v in serialisable.items() if k != "generated_at"}
    plan["plan_sha256"] = _sha256(json.dumps(stable, sort_keys=True))
    return plan


def _apply_init(plan: dict[str, Any]) -> None:
    for d in plan["dirs_to_create"]:
        Path(d).mkdir(parents=True, exist_ok=True)
    for file_info in plan["_files"]:
        p = Path(file_info["path"])
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(file_info["content"], encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@click.group()
def cli() -> None:
    """heuristichermes – Obsidian knowledge system with pluggable LLM providers."""


@cli.command()
@click.argument("vault_path")
@click.option("--apply", is_flag=True, default=False, help="Apply the plan.")
@click.option(
    "--approved-plan-sha256",
    default="",
    metavar="SHA256",
    help="SHA-256 of the plan to apply (required with --apply).",
)
def init(vault_path: str, apply: bool, approved_plan_sha256: str) -> None:
    """Initialise or adopt a vault at VAULT_PATH."""
    vault = Path(vault_path).expanduser().resolve()
    cfg = load_defaults()
    plan = _plan_init(vault, cfg)

    if not apply:
        display = {k: v for k, v in plan.items() if not k.startswith("_")}
        console.print(Panel(json.dumps(display, indent=2), title="Init plan"))
        console.print(
            f"\n[bold]Plan SHA-256:[/bold] {plan['plan_sha256']}\n\n"
            "Review the plan above, then re-run with:\n"
            f"  --apply --approved-plan-sha256 {plan['plan_sha256']}"
        )
        return

    if approved_plan_sha256 != plan["plan_sha256"]:
        console.print(
            "[red]Error:[/red] --approved-plan-sha256 does not match the current "
            "plan SHA-256.  Re-run without --apply to get the current plan."
        )
        sys.exit(1)

    _apply_init(plan)
    _log_operation(vault, {"op": "init", "ts": _now_iso(), "vault": str(vault)})
    console.print(f"[green]✓[/green] Vault initialised at {vault}")


@cli.command()
@click.argument("vault_path", required=False)
@_llm_options
def ingest(
    vault_path: str | None,
    provider_override: str | None,
    model_override: str | None,
) -> None:
    """Ingest source files from the vault inbox."""
    vault = _select_vault(vault_path)
    _require_vault(vault)
    cfg = load_vault_config(vault)

    files = _build_inbox_index(vault, cfg)
    if not files:
        console.print("[yellow]Inbox is empty.  Drop source files into inbox/ first.[/yellow]")
        return

    notes_dir = vault / cfg["notes_dir"]
    sources_dir = vault / cfg["sources_dir"]
    notes_dir.mkdir(exist_ok=True)
    sources_dir.mkdir(exist_ok=True)

    for source_path in files:
        console.print(f"Ingesting [bold]{source_path.name}[/bold] …")
        raw_text = _read_source(source_path)

        # Archive immutable copy
        content_hash = _sha256(raw_text)[:16]
        archive_name = f"{content_hash}-{source_path.name}"
        archive_path = sources_dir / archive_name
        if not archive_path.exists():
            archive_path.write_text(raw_text, encoding="utf-8")

        # Ask Hermes to synthesise a linked note
        system_prompt = textwrap.dedent("""\
            You are Hermes, a knowledge synthesis assistant.
            You write Obsidian Flavored Markdown notes that are clear, well-structured,
            and linked to related concepts using [[wikilinks]].
            Always include a YAML frontmatter block with: title, tags, source, created.
            Ground every important claim in the source text.
            Add a ## Sources section at the end with the archive filename.
        """)
        user_prompt = (
            f"Synthesise a linked knowledge note from the following source "
            f"(archived as `{archive_name}`):\n\n"
            f"---\n{raw_text[:8000]}\n---\n\n"
            "Return only the Markdown note."
        )
        note_md = _chat_completion(
            cfg,
            system_prompt=system_prompt,
            prompt=user_prompt,
            max_tokens=cfg.get("max_tokens", 4096),
            temperature=cfg.get("temperature", 0.3),
            provider_override=provider_override,
            model_override=model_override,
        )

        # Derive a title and save
        title_line = next(
            (l for l in note_md.splitlines() if l.startswith("title:")),
            None,
        )
        title = (
            title_line.split(":", 1)[1].strip().strip('"').strip("'")
            if title_line
            else source_path.stem
        )
        slug = _note_slug(title)
        note_path = notes_dir / f"{slug}.md"
        note_path.write_text(note_md, encoding="utf-8")

        # Move processed file out of inbox
        done_dir = vault / cfg["inbox_dir"] / "processed"
        done_dir.mkdir(exist_ok=True)
        source_path.rename(done_dir / source_path.name)

        _log_operation(
            vault,
            {
                "op": "ingest",
                "ts": _now_iso(),
                "source": source_path.name,
                "archive": archive_name,
                "note": str(note_path.relative_to(vault)),
            },
        )
        console.print(f"  [green]✓[/green] Created {note_path.relative_to(vault)}")


@cli.command()
@click.argument("vault_path", required=False)
@click.argument("question")
@_llm_options
def query(
    vault_path: str | None,
    question: str,
    provider_override: str | None,
    model_override: str | None,
) -> None:
    """Answer QUESTION from vault evidence (read-only)."""
    vault = _select_vault(vault_path)
    _require_vault(vault)
    cfg = load_vault_config(vault)

    notes_dir = vault / cfg["notes_dir"]
    notes = sorted(notes_dir.glob("**/*.md")) if notes_dir.exists() else []

    # Simple BM25-like keyword retrieval
    words = set(question.lower().split())
    scored: list[tuple[int, Path]] = []
    for note in notes:
        text = note.read_text(encoding="utf-8", errors="replace").lower()
        score = sum(text.count(w) for w in words)
        if score > 0:
            scored.append((score, note))
    scored.sort(key=lambda t: t[0], reverse=True)
    top_k = cfg.get("retrieve", {}).get("top_k", 10)
    relevant = [p for _, p in scored[:top_k]]

    if not relevant:
        context = "(No relevant notes found in the vault.)"
    else:
        parts = []
        for p in relevant:
            content = p.read_text(encoding="utf-8", errors="replace")[:2000]
            parts.append(f"### {p.stem}\n{content}")
        context = "\n\n".join(parts)

    system_prompt = textwrap.dedent("""\
        You are Hermes, a knowledge retrieval assistant.
        Answer the user's question using ONLY the vault evidence provided.
        Cite note titles using [[wikilinks]].
        If the evidence is insufficient, say so clearly.
        Do not hallucinate or invent facts not present in the vault.
    """)
    user_prompt = f"Question: {question}\n\nVault evidence:\n\n{context}"

    answer = _chat_completion(
        cfg,
        system_prompt=system_prompt,
        prompt=user_prompt,
        max_tokens=cfg.get("max_tokens", 4096),
        temperature=0.2,
        provider_override=provider_override,
        model_override=model_override,
    )
    console.print(Markdown(answer))
    _log_operation(
        vault,
        {
            "op": "query",
            "ts": _now_iso(),
            "question": question,
            "notes_used": [str(p.relative_to(vault)) for p in relevant],
        },
    )


@cli.command()
@click.argument("vault_path", required=False)
@click.argument("insight")
@click.option("--title", default="", help="Note title (default: derived from insight).")
@_llm_options
def save(
    vault_path: str | None,
    insight: str,
    title: str,
    provider_override: str | None,
    model_override: str | None,
) -> None:
    """Save a single scoped insight as a new note."""
    vault = _select_vault(vault_path)
    _require_vault(vault)
    cfg = load_vault_config(vault)

    system_prompt = textwrap.dedent("""\
        You are Hermes, a knowledge assistant.
        Turn the provided insight into a short, well-structured Obsidian Markdown note.
        Include YAML frontmatter with: title, tags, created.
        Use [[wikilinks]] for concepts that might already exist in the vault.
        Be concise—one idea per note.
    """)
    title_hint = f" Use the title: {title!r}." if title else ""
    user_prompt = f"Insight: {insight}{title_hint}\n\nReturn only the Markdown note."

    note_md = _chat_completion(
        cfg,
        system_prompt=system_prompt,
        prompt=user_prompt,
        max_tokens=1024,
        temperature=0.3,
        provider_override=provider_override,
        model_override=model_override,
    )

    if not title:
        title_line = next(
            (l for l in note_md.splitlines() if l.startswith("title:")),
            None,
        )
        title = (
            title_line.split(":", 1)[1].strip().strip('"').strip("'")
            if title_line
            else insight[:40]
        )

    notes_dir = vault / cfg["notes_dir"]
    notes_dir.mkdir(exist_ok=True)
    slug = _note_slug(title)
    note_path = notes_dir / f"{slug}.md"
    note_path.write_text(note_md, encoding="utf-8")

    _log_operation(vault, {"op": "save", "ts": _now_iso(), "note": str(note_path.relative_to(vault))})
    console.print(f"[green]✓[/green] Saved to {note_path.relative_to(vault)}")


@cli.command()
@click.argument("vault_path", required=False)
def lint(vault_path: str | None) -> None:
    """Report vault health: dead links, orphans, metadata gaps, stale items."""
    vault = _select_vault(vault_path)
    _require_vault(vault)
    cfg = load_vault_config(vault)

    notes_dir = vault / cfg["notes_dir"]
    notes = sorted(notes_dir.glob("**/*.md")) if notes_dir.exists() else []
    note_titles = {p.stem for p in notes}

    issues: list[str] = []
    import re

    for note in notes:
        text = note.read_text(encoding="utf-8", errors="replace")
        rel = str(note.relative_to(vault))

        # Check frontmatter
        if not text.startswith("---"):
            issues.append(f"[yellow]WARN[/yellow]  {rel}: missing YAML frontmatter")
        else:
            for field in ("title", "tags", "created"):
                if f"{field}:" not in text:
                    issues.append(f"[yellow]WARN[/yellow]  {rel}: frontmatter missing field '{field}'")

        # Dead wikilinks
        links = re.findall(r"\[\[([^\]|#]+)", text)
        for link in links:
            target = link.strip()
            if target not in note_titles:
                issues.append(f"[red]ERROR[/red] {rel}: dead link [[{target}]]")

        # Empty body (frontmatter + headings only)
        body_lines = [l for l in text.splitlines() if l.strip() and not l.startswith("#") and not l.startswith("---") and ":" not in l]
        if len(body_lines) < 2:
            issues.append(f"[yellow]WARN[/yellow]  {rel}: note body appears empty")

    # Orphan detection (notes with no incoming links)
    all_links: set[str] = set()
    for note in notes:
        text = note.read_text(encoding="utf-8", errors="replace")
        for link in re.findall(r"\[\[([^\]|#]+)", text):
            all_links.add(link.strip())
    for note in notes:
        if note.stem not in all_links and note.name != "README.md":
            issues.append(f"[dim]INFO[/dim]   {note.relative_to(vault)}: orphan (no incoming links)")

    if not issues:
        console.print("[green]✓ No issues found.[/green]")
    else:
        for issue in issues:
            console.print(issue)
        console.print(f"\n{len(issues)} issue(s) found.")

    _log_operation(vault, {"op": "lint", "ts": _now_iso(), "issues": len(issues)})


@cli.command()
@click.argument("vault_path", required=False)
@click.argument("query_text")
@click.option("--top-k", default=10, show_default=True, help="Number of results.")
def retrieve(vault_path: str | None, query_text: str, top_k: int) -> None:
    """Retrieve the most relevant notes for a query using BM25 keyword scoring."""
    vault = _select_vault(vault_path)
    _require_vault(vault)
    cfg = load_vault_config(vault)

    notes_dir = vault / cfg["notes_dir"]
    notes = sorted(notes_dir.glob("**/*.md")) if notes_dir.exists() else []
    words = set(query_text.lower().split())

    scored: list[tuple[int, Path]] = []
    for note in notes:
        text = note.read_text(encoding="utf-8", errors="replace").lower()
        score = sum(text.count(w) for w in words)
        if score > 0:
            scored.append((score, note))
    scored.sort(key=lambda t: t[0], reverse=True)

    if not scored:
        console.print("[yellow]No matching notes found.[/yellow]")
        return

    console.print(f"\nTop {min(top_k, len(scored))} results for [bold]{query_text!r}[/bold]:\n")
    for rank, (score, path) in enumerate(scored[:top_k], 1):
        console.print(f"  {rank:2d}. [bold]{path.stem}[/bold]  (score {score})  {path.relative_to(vault)}")


@cli.command()
@click.argument("vault_path", required=False)
@_llm_options
def fold(
    vault_path: str | None,
    provider_override: str | None,
    model_override: str | None,
) -> None:
    """Produce an extractive rollup of the operation log."""
    vault = _select_vault(vault_path)
    _require_vault(vault)
    cfg = load_vault_config(vault)

    log_path = vault / VAULT_LOG_FILE
    if not log_path.exists():
        console.print("[yellow]No operation log found.[/yellow]")
        return

    lines = log_path.read_text(encoding="utf-8").splitlines()
    records = []
    for line in lines:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            pass

    if not records:
        console.print("[yellow]Operation log is empty.[/yellow]")
        return

    summary_data = json.dumps(records[-200:], indent=2)

    system_prompt = textwrap.dedent("""\
        You are Hermes, a knowledge assistant.
        Summarise the provided operation log into a concise markdown report.
        Include: total operations by type, date range, notable activity, and any anomalies.
        Use plain Markdown.
    """)
    rollup = _chat_completion(
        cfg,
        system_prompt=system_prompt,
        prompt=f"Operation log:\n\n{summary_data}",
        max_tokens=1024,
        temperature=0.2,
        provider_override=provider_override,
        model_override=model_override,
    )
    console.print(Markdown(rollup))


@cli.command()
@click.argument("vault_path", required=False)
@click.argument("topic")
@_llm_options
def think(
    vault_path: str | None,
    topic: str,
    provider_override: str | None,
    model_override: str | None,
) -> None:
    """Structured observe–listen–connect–create–grow review loop for a topic."""
    vault = _select_vault(vault_path)
    _require_vault(vault)
    cfg = load_vault_config(vault)

    notes_dir = vault / cfg["notes_dir"]
    notes = sorted(notes_dir.glob("**/*.md")) if notes_dir.exists() else []

    # Retrieve relevant notes
    words = set(topic.lower().split())
    scored: list[tuple[int, Path]] = []
    for note in notes:
        text = note.read_text(encoding="utf-8", errors="replace").lower()
        score = sum(text.count(w) for w in words)
        if score > 0:
            scored.append((score, note))
    scored.sort(key=lambda t: t[0], reverse=True)
    relevant = [p for _, p in scored[:5]]

    context_parts = []
    for p in relevant:
        content = p.read_text(encoding="utf-8", errors="replace")[:2000]
        context_parts.append(f"### {p.stem}\n{content}")
    context = "\n\n".join(context_parts) or "(No relevant notes found.)"

    system_prompt = textwrap.dedent("""\
        You are Hermes, a reflective thinking assistant.
        Apply the Observe–Listen–Connect–Create–Grow (OLCCG) loop to the topic.

        ## Observe
        What do the vault notes reveal about this topic?

        ## Listen
        What patterns, tensions, or open questions emerge?

        ## Connect
        What wikilinks to existing or new concepts are suggested?

        ## Create
        Propose one concrete new note or improvement to the vault.

        ## Grow
        What next action would compound knowledge most effectively?

        Be specific and cite vault evidence with [[wikilinks]].
    """)
    user_prompt = f"Topic: {topic}\n\nVault evidence:\n\n{context}"

    reflection = _chat_completion(
        cfg,
        system_prompt=system_prompt,
        prompt=user_prompt,
        max_tokens=cfg.get("max_tokens", 4096),
        temperature=0.4,
        provider_override=provider_override,
        model_override=model_override,
    )
    console.print(Markdown(reflection))
    _log_operation(vault, {"op": "think", "ts": _now_iso(), "topic": topic})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
