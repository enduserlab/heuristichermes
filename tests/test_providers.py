from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts import hermes
from scripts.providers import generate_response, resolve_llm_settings


class ProviderConfigTests(unittest.TestCase):
    def test_resolve_llm_settings_uses_provider_specific_defaults(self) -> None:
        cfg = {
            "llm": {
                "default_provider": "minimax",
                "providers": {
                    "minimax": {"model": "MiniMax-M3"},
                    "openai": {"model": "gpt-4o-mini"},
                },
            }
        }

        self.assertEqual(
            resolve_llm_settings(cfg),
            {
                "provider": "minimax",
                "model": "MiniMax-M3",
                "base_url": "",
            },
        )
        self.assertEqual(
            resolve_llm_settings(cfg, provider="openai"),
            {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "base_url": "",
            },
        )

    def test_load_vault_config_deep_merges_llm_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir)
            (vault / hermes.VAULT_CONFIG_FILE).write_text(
                json.dumps({"llm": {"default_provider": "openai"}}),
                encoding="utf-8",
            )

            cfg = hermes.load_vault_config(vault)

        self.assertEqual(cfg["llm"]["default_provider"], "openai")
        self.assertIn("minimax", cfg["llm"]["providers"])
        self.assertEqual(cfg["llm"]["providers"]["openai"]["model"], "gpt-4o-mini")

    def test_load_vault_config_supports_legacy_model_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir)
            (vault / hermes.VAULT_CONFIG_FILE).write_text(
                json.dumps({"model": "MiniMax-M2"}),
                encoding="utf-8",
            )

            cfg = hermes.load_vault_config(vault)

        self.assertEqual(cfg["llm"]["default_provider"], "minimax")
        self.assertEqual(cfg["llm"]["providers"]["minimax"]["model"], "MiniMax-M2")

    @patch.dict("os.environ", {"OPENAI_BASE_URL": "https://override.example/v1"}, clear=True)
    def test_resolve_llm_settings_prefers_base_url_environment_override(self) -> None:
        cfg = {
            "llm": {
                "default_provider": "openai",
                "providers": {
                    "openai": {
                        "model": "gpt-4o-mini",
                        "base_url": "https://config.example/v1",
                    }
                },
            }
        }

        resolved = resolve_llm_settings(cfg)

        self.assertEqual(resolved["base_url"], "https://override.example/v1")


class ProviderRequestTests(unittest.TestCase):
    @patch.dict("os.environ", {"MINIMAX_API_KEY": "minimax-key"}, clear=True)
    @patch("scripts.providers.requests.post")
    def test_generate_response_uses_openai_compatible_payload(
        self,
        mock_post: Mock,
    ) -> None:
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "hello from minimax"}}]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        response = generate_response(
            provider="minimax",
            model="MiniMax-M3",
            prompt="hello",
            system_prompt="system",
            temperature=0.2,
            max_tokens=256,
        )

        self.assertEqual(response, "hello from minimax")
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["model"], "MiniMax-M3")
        self.assertEqual(kwargs["json"]["messages"][0]["role"], "system")
        self.assertEqual(kwargs["json"]["messages"][1]["content"], "hello")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer " + "minimax-key")

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "anthropic-key"}, clear=True)
    @patch("scripts.providers.requests.post")
    def test_generate_response_uses_anthropic_messages_api(
        self,
        mock_post: Mock,
    ) -> None:
        mock_response = Mock()
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "hello from claude"}]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        response = generate_response(
            provider="anthropic",
            model="claude-3-5-sonnet-latest",
            prompt="hello",
            system_prompt="system",
            temperature=0.1,
            max_tokens=512,
        )

        self.assertEqual(response, "hello from claude")
        _, kwargs = mock_post.call_args
        self.assertTrue(str(mock_post.call_args.args[0]).endswith("/messages"))
        self.assertEqual(kwargs["json"]["system"], "system")
        self.assertEqual(kwargs["json"]["messages"][0]["content"], "hello")
        self.assertEqual(kwargs["headers"]["x-api-key"], "anthropic-key")


if __name__ == "__main__":
    unittest.main()
