from __future__ import annotations

import os
from typing import Any

import requests

PROVIDER_SPECS: dict[str, dict[str, Any]] = {
    "minimax": {
        "api_key_env": "MINIMAX_API_KEY",
        "base_url_env": "MINIMAX_BASE_URL",
        "default_base_url": "https://api.minimax.io/v1",
    },
    "anthropic": {
        "api_key_env": "ANTHROPIC_API_KEY",
        "base_url_env": "ANTHROPIC_BASE_URL",
        "default_base_url": "https://api.anthropic.com/v1",
    },
    "openai": {
        "api_key_env": "OPENAI_API_KEY",
        "base_url_env": "OPENAI_BASE_URL",
        "default_base_url": "https://api.openai.com/v1",
    },
    "xai": {
        "api_key_env": "XAI_API_KEY",
        "base_url_env": "XAI_BASE_URL",
        "default_base_url": "https://api.x.ai/v1",
    },
}

SUPPORTED_PROVIDERS = tuple(PROVIDER_SPECS.keys())


def resolve_llm_settings(
    cfg: dict[str, Any],
    *,
    provider: str | None = None,
    model: str | None = None,
) -> dict[str, str]:
    llm_cfg = cfg.get("llm", {})
    provider_name = (
        provider
        or os.environ.get("HERMES_PROVIDER")
        or llm_cfg.get("default_provider")
        or cfg.get("provider")
        or "minimax"
    ).strip().lower()
    if provider_name not in PROVIDER_SPECS:
        raise ValueError(
            f"Unsupported provider '{provider_name}'. "
            f"Supported providers: {', '.join(SUPPORTED_PROVIDERS)}"
        )
    provider_spec = PROVIDER_SPECS[provider_name]
    provider_cfg = llm_cfg.get("providers", {}).get(provider_name, {})
    resolved_model = (
        model
        or os.environ.get("HERMES_MODEL")
        or provider_cfg.get("model")
        or cfg.get("model")
    )
    if not resolved_model:
        raise ValueError(f"No model configured for provider '{provider_name}'.")
    return {
        "provider": provider_name,
        "model": resolved_model,
        "base_url": (
            os.environ.get(provider_spec["base_url_env"])
            or provider_cfg.get("base_url", "")
            or provider_spec["default_base_url"]
        ),
    }


def generate_response(
    provider: str,
    model: str,
    prompt: str,
    temperature: float,
    max_tokens: int,
    system_prompt: str | None = None,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    timeout: int = 120,
) -> str:
    provider_name = provider.strip().lower()
    if provider_name not in PROVIDER_SPECS:
        raise ValueError(
            f"Unsupported provider '{provider_name}'. "
            f"Supported providers: {', '.join(SUPPORTED_PROVIDERS)}"
        )
    spec = PROVIDER_SPECS[provider_name]
    resolved_api_key = api_key or os.environ.get(spec["api_key_env"], "")
    if not resolved_api_key:
        raise OSError(
            f"{spec['api_key_env']} is not set. "
            "Copy .env.example to .env and add your key."
        )
    resolved_base_url = (
        base_url
        or os.environ.get(spec["base_url_env"], spec["default_base_url"])
    ).rstrip("/")

    if provider_name == "anthropic":
        return _generate_anthropic_response(
            api_key=resolved_api_key,
            base_url=resolved_base_url,
            model=model,
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    return _generate_openai_compatible_response(
        api_key=resolved_api_key,
        base_url=resolved_base_url,
        model=model,
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )


def _generate_openai_compatible_response(
    *,
    api_key: str,
    base_url: str,
    model: str,
    prompt: str,
    system_prompt: str | None,
    temperature: float,
    max_tokens: int,
    timeout: int,
) -> str:
    messages = [{"role": "user", "content": prompt}]
    if system_prompt:
        messages.insert(0, {"role": "system", "content": system_prompt})
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    resp = requests.post(
        f"{base_url}/chat/completions",
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"Unexpected API response shape: {data}") from exc
    return _coerce_response_text(content, data)


def _generate_anthropic_response(
    *,
    api_key: str,
    base_url: str,
    model: str,
    prompt: str,
    system_prompt: str | None,
    temperature: float,
    max_tokens: int,
    timeout: int,
) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if system_prompt:
        payload["system"] = system_prompt
    resp = requests.post(
        f"{base_url}/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    try:
        blocks = data["content"]
    except KeyError as exc:
        raise RuntimeError(f"Unexpected API response shape: {data}") from exc
    text = _coerce_response_text(blocks, data)
    if not text:
        raise RuntimeError(f"Unexpected API response shape: {data}")
    return text


def _coerce_response_text(content: Any, data: dict[str, Any]) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if text:
                    parts.append(text)
        if parts:
            return "".join(parts).strip()
    raise RuntimeError(f"Unexpected API response shape: {data}")
