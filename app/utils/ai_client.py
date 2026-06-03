"""
LLM 客户端封装 — 6 provider 统一接口

支持的 provider：
  deepseek    → OpenAI SDK, https://api.deepseek.com/v1
  openai      → OpenAI SDK, https://api.openai.com/v1
  anthropic   → Anthropic SDK（独立，非 OpenAI 兼容）
  qwen        → OpenAI SDK, DashScope compatible endpoint
  dashscope   → 同 qwen
  siliconflow → OpenAI SDK, https://api.siliconflow.cn/v1
  其他        → OpenAI SDK 兜底（需提供 base_url）

model 前缀路由（可通过 model 字段覆盖 provider）：
  LLM_MODEL=anthropic:claude-opus-4-7   → provider 自动切换为 anthropic
  LLM_MODEL=qwen:qwen-plus              → provider 自动切换为 qwen
"""

import json
import re
from typing import Any, Dict, Optional

from app.utils.logger import logger


_OPENAI_COMPATIBLE: Dict[str, str] = {
    "deepseek":    "https://api.deepseek.com/v1",
    "openai":      "https://api.openai.com/v1",
    "qwen":        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "dashscope":   "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "siliconflow": "https://api.siliconflow.cn/v1",
}

_DEFAULT_MODELS: Dict[str, str] = {
    "deepseek":    "deepseek-chat",
    "openai":      "gpt-4o-mini",
    "anthropic":   "claude-sonnet-4-6",
    "qwen":        "qwen-plus",
    "dashscope":   "qwen-plus",
    "siliconflow": "Qwen/Qwen2.5-7B-Instruct",
}

_KNOWN_PROVIDERS = set(_OPENAI_COMPATIBLE) | {"anthropic"}


class LLMClient:
    """统一的 LLM 客户端接口"""

    def __init__(
        self,
        provider: str = "deepseek",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "deepseek-chat",
    ):
        # model 前缀路由：若 model 形如 "provider:model_name"，用前缀覆盖 provider
        if ":" in model:
            derived, _, model_name = model.partition(":")
            if derived in _KNOWN_PROVIDERS:
                provider = derived
                model = model_name

        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url
        self.model = model or _DEFAULT_MODELS.get(provider, "")
        self._client = None

        if provider == "anthropic":
            self._init_anthropic()
        elif provider in _OPENAI_COMPATIBLE or base_url:
            self._init_openai_compatible()
        else:
            logger.warning(f"未知 provider '{provider}'，尝试 OpenAI 兼容模式（需配置 base_url）")
            self._init_openai_compatible()

        logger.debug(f"LLMClient 初始化: provider={self.provider}, model={self.model}")

    # ─── 工厂方法 ──────────────────────────────────────────────────────────────

    @classmethod
    def from_settings(cls) -> "LLMClient":
        from app.config import get_settings
        s = get_settings()
        api_key = s.LLM_API_KEY
        # Anthropic provider 优先使用专用 key
        if s.LLM_PROVIDER == "anthropic" and not api_key:
            api_key = getattr(s, "ANTHROPIC_API_KEY", "")
        return cls(
            provider=s.LLM_PROVIDER,
            api_key=api_key,
            base_url=s.LLM_BASE_URL,
            model=s.LLM_MODEL,
        )

    # ─── 初始化 ────────────────────────────────────────────────────────────────

    def _init_anthropic(self):
        try:
            import anthropic
        except ImportError:
            raise ImportError("请安装 Anthropic SDK: pip install anthropic")
        self._client = anthropic.Anthropic(api_key=self.api_key)

    def _init_openai_compatible(self):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("请安装 openai: pip install openai")
        base = self.base_url or _OPENAI_COMPATIBLE.get(self.provider, "https://api.openai.com/v1")
        self._client = OpenAI(api_key=self.api_key, base_url=base)

    # ─── 公开接口 ──────────────────────────────────────────────────────────────

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        if not self._client:
            raise RuntimeError("LLM client not initialized")
        try:
            if self.provider == "anthropic":
                return self._generate_anthropic(prompt, system_prompt, temperature, max_tokens)
            return self._generate_openai(prompt, system_prompt, temperature, max_tokens)
        except Exception as e:
            raise RuntimeError(f"LLM 生成失败 [{self.provider}/{self.model}]: {e}") from e

    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        json_prompt = prompt + "\n\n重要：只返回标准 JSON，不要有其他说明文字。"
        response = self.generate(
            prompt=json_prompt,
            system_prompt=system_prompt,
            temperature=temperature,
        )
        return self._extract_json(response)

    # ─── 私有生成方法 ──────────────────────────────────────────────────────────

    def _generate_openai(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    def _generate_anthropic(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> str:
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        response = self._client.messages.create(**kwargs)
        return response.content[0].text

    # ─── JSON 提取 ──────────────────────────────────────────────────────────────

    def _extract_json(self, text: str) -> Dict[str, Any]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        raise ValueError(f"无法从 LLM 响应中提取 JSON: {text[:200]}")
