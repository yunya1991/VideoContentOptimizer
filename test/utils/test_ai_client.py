"""
LLMClient 单元测试 — 6 provider 路由 + model 前缀覆盖 + generate/generate_json

测试范围：
  - deepseek/openai/qwen/dashscope/siliconflow → OpenAI 兼容 SDK 初始化
  - anthropic → Anthropic SDK 初始化，generate() 走 messages.create()
  - 未知 provider → 兜底，不抛 ValueError
  - model 前缀路由（anthropic:claude-opus-4-7 → provider 切换为 anthropic）
  - generate() 成功返回字符串
  - generate_json() 三种 JSON 格式容错（纯 JSON / ```json``` / 裸 {}）
  - generate_json() 格式不可解析 → ValueError
  - from_settings() 工厂方法读取 settings
  - Anthropic system_prompt 作为顶层参数传递
"""

from unittest.mock import MagicMock, call, patch

import pytest


# ─── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _patch_settings(mock_settings):
    with patch("app.config.get_settings", return_value=mock_settings):
        yield


def _make_openai_client(response_text: str = "hello"):
    """构造 mock OpenAI client，chat.completions.create 返回指定文本。"""
    choice = MagicMock()
    choice.message.content = response_text
    completion = MagicMock()
    completion.choices = [choice]
    client = MagicMock()
    client.chat.completions.create.return_value = completion
    return client


def _make_anthropic_client(response_text: str = "hello anthropic"):
    """构造 mock Anthropic client，messages.create 返回指定文本。"""
    content_block = MagicMock()
    content_block.text = response_text
    message = MagicMock()
    message.content = [content_block]
    client = MagicMock()
    client.messages.create.return_value = message
    return client


# ═══════════════════════════════════════════════════════════════════════════════
# Section 1 — provider 路由：OpenAI 兼容层
# ═══════════════════════════════════════════════════════════════════════════════

class TestOpenAICompatibleProviders:

    @pytest.mark.parametrize("provider,expected_base_url_fragment", [
        ("deepseek",    "deepseek.com"),
        ("openai",      "openai.com"),
        ("qwen",        "dashscope"),
        ("dashscope",   "dashscope"),
        ("siliconflow", "siliconflow.cn"),
    ])
    def test_provider_uses_correct_base_url(self, provider, expected_base_url_fragment):
        from openai import OpenAI as RealOpenAI
        captured = {}

        class CapturingOpenAI:
            def __init__(self, api_key, base_url=None):
                captured["base_url"] = base_url or ""
                self.chat = MagicMock()

        with patch("app.utils.ai_client.OpenAI", CapturingOpenAI, create=True):
            # We can't patch inside the module easily without reloading;
            # so we patch the openai import path used in the module
            with patch("openai.OpenAI", CapturingOpenAI):
                from app.utils import ai_client
                import importlib; importlib.reload(ai_client)
                ai_client.LLMClient(provider=provider, api_key="k", model="m")

        assert expected_base_url_fragment in captured.get("base_url", ""), \
            f"{provider} base_url should contain '{expected_base_url_fragment}', got '{captured.get('base_url')}'"

    def test_unknown_provider_no_value_error(self):
        """未知 provider 不抛 ValueError，使用 OpenAI 兼容兜底。"""
        with patch("openai.OpenAI", return_value=MagicMock()):
            from app.utils import ai_client
            import importlib; importlib.reload(ai_client)
            client = ai_client.LLMClient(
                provider="unknown_future_provider",
                api_key="k",
                base_url="https://example.com/v1",
                model="some-model",
            )
        assert client.provider == "unknown_future_provider"


# ═══════════════════════════════════════════════════════════════════════════════
# Section 2 — provider 路由：Anthropic
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnthropicProvider:

    def _make_client(self, model="claude-sonnet-4-6"):
        mock_anthropic_module = MagicMock()
        mock_anthropic_module.Anthropic.return_value = _make_anthropic_client()
        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            from app.utils import ai_client
            import importlib; importlib.reload(ai_client)
            c = ai_client.LLMClient(provider="anthropic", api_key="test_key", model=model)
        return c, mock_anthropic_module

    def test_anthropic_sdk_used(self):
        mock_anthropic_module = MagicMock()
        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            from app.utils import ai_client
            import importlib; importlib.reload(ai_client)
            ai_client.LLMClient(provider="anthropic", api_key="key", model="claude-sonnet-4-6")
        mock_anthropic_module.Anthropic.assert_called_once_with(api_key="key")

    def test_generate_uses_messages_create(self):
        mock_anthropic_module = MagicMock()
        mock_client = _make_anthropic_client("response text")
        mock_anthropic_module.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            from app.utils import ai_client
            import importlib; importlib.reload(ai_client)
            c = ai_client.LLMClient(provider="anthropic", api_key="key", model="claude-sonnet-4-6")
            result = c.generate("prompt text")

        assert result == "response text"
        mock_client.messages.create.assert_called_once()

    def test_system_prompt_as_top_level_param(self):
        """Anthropic API 的 system 参数是顶层字段，不在 messages 列表里。"""
        mock_anthropic_module = MagicMock()
        mock_client = _make_anthropic_client()
        mock_anthropic_module.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            from app.utils import ai_client
            import importlib; importlib.reload(ai_client)
            c = ai_client.LLMClient(provider="anthropic", api_key="key", model="claude-sonnet-4-6")
            c.generate("prompt", system_prompt="You are helpful")

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs.get("system") == "You are helpful"
        # system must NOT appear in messages list
        for msg in call_kwargs.get("messages", []):
            assert msg.get("role") != "system"

    def test_no_system_prompt_no_system_key(self):
        mock_anthropic_module = MagicMock()
        mock_client = _make_anthropic_client()
        mock_anthropic_module.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            from app.utils import ai_client
            import importlib; importlib.reload(ai_client)
            c = ai_client.LLMClient(provider="anthropic", api_key="key", model="claude-sonnet-4-6")
            c.generate("prompt")

        call_kwargs = mock_client.messages.create.call_args[1]
        assert "system" not in call_kwargs

    def test_import_error_on_missing_anthropic(self):
        with patch.dict("sys.modules", {"anthropic": None}):
            from app.utils import ai_client
            import importlib; importlib.reload(ai_client)
            with pytest.raises(ImportError, match="pip install anthropic"):
                ai_client.LLMClient(provider="anthropic", api_key="key", model="claude-sonnet-4-6")


# ═══════════════════════════════════════════════════════════════════════════════
# Section 3 — model 前缀路由
# ═══════════════════════════════════════════════════════════════════════════════

class TestModelPrefixRouting:

    @pytest.mark.parametrize("model_str,expected_provider,expected_model", [
        ("anthropic:claude-opus-4-7",   "anthropic",   "claude-opus-4-7"),
        ("anthropic:claude-sonnet-4-6", "anthropic",   "claude-sonnet-4-6"),
        ("qwen:qwen-plus",              "qwen",        "qwen-plus"),
        ("deepseek:deepseek-chat",      "deepseek",    "deepseek-chat"),
        ("deepseek-chat",               "deepseek",    "deepseek-chat"),  # no prefix → unchanged
    ])
    def test_prefix_overrides_provider(self, model_str, expected_provider, expected_model):
        mock_anthropic = MagicMock()
        mock_openai = MagicMock()

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}), \
             patch("openai.OpenAI", return_value=mock_openai):
            from app.utils import ai_client
            import importlib; importlib.reload(ai_client)
            c = ai_client.LLMClient(
                provider="deepseek",   # initial provider — may be overridden by model prefix
                api_key="key",
                model=model_str,
            )

        assert c.provider == expected_provider
        assert c.model == expected_model

    def test_unknown_prefix_leaves_provider_unchanged(self):
        with patch("openai.OpenAI", return_value=MagicMock()):
            from app.utils import ai_client
            import importlib; importlib.reload(ai_client)
            c = ai_client.LLMClient(
                provider="deepseek",
                api_key="key",
                model="unknown:some-model",
            )
        assert c.provider == "deepseek"
        assert c.model == "some-model"


# ═══════════════════════════════════════════════════════════════════════════════
# Section 4 — generate() OpenAI 路径
# ═══════════════════════════════════════════════════════════════════════════════

class TestGenerateOpenAI:

    @pytest.fixture
    def client(self):
        mock_oa = _make_openai_client("test response")
        with patch("openai.OpenAI", return_value=mock_oa):
            from app.utils import ai_client
            import importlib; importlib.reload(ai_client)
            c = ai_client.LLMClient(provider="deepseek", api_key="key", model="deepseek-chat")
        c._client = mock_oa
        return c, mock_oa

    def test_generate_returns_content(self, client):
        c, _ = client
        result = c.generate("hello")
        assert result == "test response"

    def test_system_prompt_in_messages(self, client):
        c, mock_oa = client
        c.generate("prompt", system_prompt="be concise")
        messages = mock_oa.chat.completions.create.call_args[1]["messages"]
        roles = [m["role"] for m in messages]
        assert roles[0] == "system"
        assert roles[1] == "user"

    def test_temperature_and_max_tokens_passed(self, client):
        c, mock_oa = client
        c.generate("p", temperature=0.1, max_tokens=100)
        kwargs = mock_oa.chat.completions.create.call_args[1]
        assert kwargs["temperature"] == 0.1
        assert kwargs["max_tokens"] == 100

    def test_generate_exception_raises_runtime_error(self, client):
        c, mock_oa = client
        mock_oa.chat.completions.create.side_effect = Exception("api error")
        with pytest.raises(RuntimeError, match="LLM 生成失败"):
            c.generate("fail")


# ═══════════════════════════════════════════════════════════════════════════════
# Section 5 — generate_json() 格式容错
# ═══════════════════════════════════════════════════════════════════════════════

class TestGenerateJSON:

    @pytest.fixture
    def client(self):
        mock_oa = MagicMock()
        with patch("openai.OpenAI", return_value=mock_oa):
            from app.utils import ai_client
            import importlib; importlib.reload(ai_client)
            c = ai_client.LLMClient(provider="deepseek", api_key="key", model="m")
        c._client = mock_oa
        return c, mock_oa

    def _set_response(self, mock_oa, text):
        choice = MagicMock()
        choice.message.content = text
        mock_oa.chat.completions.create.return_value = MagicMock(choices=[choice])

    def test_pure_json(self, client):
        c, mock_oa = client
        self._set_response(mock_oa, '{"title": "hello", "score": 0.9}')
        result = c.generate_json("prompt")
        assert result["title"] == "hello"
        assert result["score"] == 0.9

    def test_json_fenced_with_backticks(self, client):
        c, mock_oa = client
        self._set_response(mock_oa, '```json\n{"key": "value"}\n```')
        result = c.generate_json("prompt")
        assert result["key"] == "value"

    def test_bare_json_in_text(self, client):
        c, mock_oa = client
        self._set_response(mock_oa, '这是分析结果：{"titles": ["a", "b"]} 以上。')
        result = c.generate_json("prompt")
        assert result["titles"] == ["a", "b"]

    def test_unparseable_raises_value_error(self, client):
        c, mock_oa = client
        self._set_response(mock_oa, "这根本不是 JSON")
        with pytest.raises(ValueError, match="无法从 LLM 响应中提取 JSON"):
            c.generate_json("prompt")

    def test_json_hint_appended_to_prompt(self, client):
        c, mock_oa = client
        self._set_response(mock_oa, '{"x": 1}')
        c.generate_json("基础 prompt")
        actual_prompt = mock_oa.chat.completions.create.call_args[1]["messages"][-1]["content"]
        assert "JSON" in actual_prompt


# ═══════════════════════════════════════════════════════════════════════════════
# Section 6 — from_settings() 工厂方法
# ═══════════════════════════════════════════════════════════════════════════════

class TestFromSettings:

    def test_from_settings_reads_provider_and_model(self, mock_settings):
        mock_settings.LLM_PROVIDER = "deepseek"
        mock_settings.LLM_API_KEY = "test_key"
        mock_settings.LLM_BASE_URL = None
        mock_settings.LLM_MODEL = "deepseek-chat"

        with patch("openai.OpenAI", return_value=MagicMock()):
            with patch("app.config.get_settings", return_value=mock_settings):
                from app.utils import ai_client
                import importlib; importlib.reload(ai_client)
                c = ai_client.LLMClient.from_settings()

        assert c.provider == "deepseek"
        assert c.model == "deepseek-chat"
        assert c.api_key == "test_key"

    def test_from_settings_uses_anthropic_key_for_anthropic(self, mock_settings):
        mock_settings.LLM_PROVIDER = "anthropic"
        mock_settings.LLM_API_KEY = ""
        mock_settings.ANTHROPIC_API_KEY = "ant_key"
        mock_settings.LLM_BASE_URL = None
        mock_settings.LLM_MODEL = "claude-sonnet-4-6"

        mock_anthropic = MagicMock()
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            with patch("app.config.get_settings", return_value=mock_settings):
                from app.utils import ai_client
                import importlib; importlib.reload(ai_client)
                c = ai_client.LLMClient.from_settings()

        mock_anthropic.Anthropic.assert_called_with(api_key="ant_key")
