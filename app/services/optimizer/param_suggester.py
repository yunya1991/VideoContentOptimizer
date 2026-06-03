"""
优化参数推荐器 - 基于内容生成 3 个优化方向档案
"""

import json
from typing import List, Optional

from app.models.schema import (
    OptimizationParams, OptimizationProfile,
    SuggestParamsResponse, VideoIntent,
)
from app.utils.ai_client import LLMClient
from app.utils.logger import logger
from app.config import get_settings

settings = get_settings()

_STATIC_PROFILES = [
    OptimizationProfile(
        id="viral",
        name="🔥 爆款流量型",
        description="好奇心标题 + 强 hook 开场，冲击流量池",
        why="适合大多数内容，以互动和曝光为首要目标",
        params=OptimizationParams(
            optimization_goal="ctr",
            tone="energetic",
            num_variants=5,
            optimization_types=["script", "title"],
        ),
    ),
    OptimizationProfile(
        id="knowledge",
        name="📚 知识干货型",
        description="实用价值标题 + 结构化文案，建立专业信任",
        why="适合教程/测评类内容，以留存和涨粉为目标",
        params=OptimizationParams(
            optimization_goal="engagement",
            tone="professional",
            num_variants=3,
            optimization_types=["script", "title"],
        ),
    ),
    OptimizationProfile(
        id="brand",
        name="💼 品牌调性型",
        description="收益承诺标题 + 温和语调，强化品牌一致性",
        why="适合品牌/商业内容，以长效品牌价值为目标",
        params=OptimizationParams(
            optimization_goal="brand",
            tone="casual",
            num_variants=3,
            optimization_types=["script", "title"],
        ),
    ),
]

_SUGGEST_PROMPT = """你是短视频内容策略专家。根据以下视频文案内容，为用户推荐 3 个优化方向。

视频文案（前500字）：
{transcript}

关键词：{keywords}
视频意图：{intent_desc}
{soul_context}
请返回严格的 JSON 格式，不要有任何额外说明：
{{
  "profiles": [
    {{
      "id": "viral",
      "name": "🔥 爆款流量型",
      "description": "一句话描述此方向的核心策略",
      "why": "针对这段具体内容，解释为什么推荐此方向（1-2句）",
      "params": {{
        "target_platform": "douyin",
        "optimization_goal": "ctr",
        "tone": "energetic",
        "num_variants": 5,
        "optimization_types": ["script", "title"]
      }}
    }},
    {{
      "id": "knowledge",
      "name": "📚 知识干货型",
      "description": "一句话描述此方向的核心策略",
      "why": "针对这段具体内容，解释为什么推荐此方向（1-2句）",
      "params": {{
        "target_platform": "douyin",
        "optimization_goal": "engagement",
        "tone": "professional",
        "num_variants": 3,
        "optimization_types": ["script", "title"]
      }}
    }},
    {{
      "id": "brand",
      "name": "💼 品牌调性型",
      "description": "一句话描述此方向的核心策略",
      "why": "针对这段具体内容，解释为什么推荐此方向（1-2句）",
      "params": {{
        "target_platform": "douyin",
        "optimization_goal": "brand",
        "tone": "casual",
        "num_variants": 3,
        "optimization_types": ["script", "title"]
      }}
    }}
  ],
  "default_index": 0
}}

optimization_goal 可选值：engagement / ctr / brand / viral
tone 可选值：energetic / professional / casual / emotional
target_platform 可选值：douyin / xiaohongshu / weixin
"""


class ParamSuggester:
    """根据视频内容推荐优化参数档案"""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or self._create_default_client()

    def _create_default_client(self) -> Optional[LLMClient]:
        if not settings.LLM_API_KEY:
            return None
        try:
            return LLMClient(
                provider=settings.LLM_PROVIDER,
                api_key=settings.LLM_API_KEY,
                base_url=settings.LLM_BASE_URL,
                model=settings.LLM_MODEL,
            )
        except Exception as e:
            logger.warning(f"ParamSuggester: LLM 客户端创建失败: {e}")
            return None

    def _get_soul_context(self) -> str:
        """读取 Soul 画像，提炼用户偏好摘要注入 prompt。Soul 不可用时返回空字符串。"""
        try:
            from app.services.evolution.souls.soul_manager import SoulManager
            sm = SoulManager()
            soul = sm.get_soul("default")
            parts = []
            if soul.decisions.preferred_strategies:
                parts.append("历史偏好方向：" + "、".join(soul.decisions.preferred_strategies[-3:]))
            risk = soul.decisions.risk_tolerance
            if risk >= 0.7:
                parts.append("风险偏好：偏高（倾向爆款/流量型）")
            elif risk <= 0.3:
                parts.append("风险偏好：偏低（倾向品牌/稳健型）")
            if soul.communication.tone and soul.communication.tone != "professional":
                parts.append(f"沟通偏好：{soul.communication.tone}")
            top_platforms = [e.domain for e in sorted(soul.expertise, key=lambda x: x.proficiency, reverse=True)
                             if e.domain in ("douyin", "xiaohongshu", "weixin")][:2]
            if top_platforms:
                parts.append("常用平台：" + "、".join(top_platforms))
            if not parts:
                return ""
            return "\n用户历史偏好（请优先参考）：" + "；".join(parts) + "\n"
        except Exception as e:
            logger.debug(f"ParamSuggester: Soul 画像读取失败（降级忽略）: {e}")
            return ""

    def suggest(
        self,
        transcript: str,
        keywords: List[str] = None,
        intent: Optional[VideoIntent] = None,
    ) -> SuggestParamsResponse:
        """
        生成 3 个优化方向推荐卡片。
        读取 Soul 画像个性化推荐；LLM 不可用时降级为静态默认档案。
        """
        if not self.llm_client:
            logger.info("ParamSuggester: LLM 不可用，使用静态默认档案")
            return SuggestParamsResponse(profiles=_STATIC_PROFILES, default_index=0)

        keywords = keywords or []
        intent_desc = ""
        if intent:
            intent_desc = f"{intent.category} / {intent.sub_category} / 情感:{intent.emotion}"

        soul_context = self._get_soul_context()
        if soul_context:
            logger.info(f"ParamSuggester: 已注入 Soul 画像偏好")

        prompt = _SUGGEST_PROMPT.format(
            transcript=transcript[:500],
            keywords="、".join(keywords[:10]) if keywords else "无",
            intent_desc=intent_desc or "未知",
            soul_context=soul_context,
        )

        try:
            result = self.llm_client.generate_json(
                messages=[{"role": "user", "content": prompt}]
            )
            profiles = [
                OptimizationProfile(
                    id=p["id"],
                    name=p["name"],
                    description=p["description"],
                    why=p["why"],
                    params=OptimizationParams(**p["params"]),
                )
                for p in result.get("profiles", [])
            ]
            if len(profiles) != 3:
                raise ValueError(f"期望3个档案，实际得到 {len(profiles)} 个")
            return SuggestParamsResponse(
                profiles=profiles,
                default_index=int(result.get("default_index", 0)),
            )
        except Exception as e:
            logger.warning(f"ParamSuggester: LLM 生成失败，降级为静态档案: {e}")
            return SuggestParamsResponse(profiles=_STATIC_PROFILES, default_index=0)
