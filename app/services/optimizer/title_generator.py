"""
标题生成器（基于 LLM）
"""

from typing import List, Dict, Optional
from app.models.schema import VideoIntent, TitleVariant
from app.utils.ai_client import LLMClient
from app.utils.logger import logger
from app.config import get_settings
from app.services.evolution.souls.soul_manager import SoulManager

settings = get_settings()

class TitleGenerator:
    """为视频生成吸引人的标题"""
    
    TITLE_STYLES = {
        "curiosity_gap": "制造好奇心缺口",
        "emotional": "激发情感",
        "practical": "强调实用价值",
        "controversy": "引发讨论",
        "fomo": "制造紧迫感",
        "benefit": "承诺收益",
        "celebrity": "名人效应",
        "number": "数字列表"
    }
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        初始化标题生成器
        
        Args:
            llm_client: LLM 客户端实例
        """
        self.llm_client = llm_client or self._create_default_client()
        self.soul_manager = SoulManager()
    
    def _create_default_client(self) -> Optional[LLMClient]:
        """创建默认的 LLM 客户端"""
        if not settings.LLM_API_KEY:
            return None
        
        try:
            return LLMClient(
                provider=settings.LLM_PROVIDER,
                api_key=settings.LLM_API_KEY,
                base_url=settings.LLM_BASE_URL,
                model=settings.LLM_MODEL
            )
        except Exception as e:
            logger.warning(f"创建 LLM 客户端失败: {e}")
            return None
    
    def generate_titles(
        self,
        transcript: str,
        keywords: List[str],
        intent: VideoIntent,
        num_titles: int = 5,
        target_platform: str = "douyin"
    ) -> List[Dict]:
        """
        为视频生成多个不同风格的标题
        
        Args:
            transcript: 转录文本
            keywords: 关键词列表
            intent: 视频意图
            num_titles: 标题数量
            target_platform: 目标平台
            
        Returns:
            List[Dict]: 标题列表，每个包含 title, style, estimated_ctr 等
        """
        if not self.llm_client:
            return self._fallback_titles(transcript)
        
        prompt = self._build_prompt(
            transcript, keywords, intent, num_titles, target_platform
        )
        
        # 注入 Soul 动态内容
        prompt = self.soul_manager.inject_soul_into_prompt(
            prompt=prompt,
            task_type='title_generation',
            soul_id='default'
        )
        
        try:
            result = self.llm_client.generate_json(prompt)
            titles = result.get("titles", [])
            
            # 验证和补充字段
            for title in titles:
                if "title" not in title:
                    continue
                title.setdefault("style", "unknown")
                title.setdefault("estimated_ctr", 0.1)
                title.setdefault("rationale", "")
            
            return titles[:num_titles]
        
        except Exception as e:
            logger.warning(f"标题生成失败: {e}")
            return self._fallback_titles(transcript)
    
    def _build_prompt(
        self,
        transcript: str,
        keywords: List[str],
        intent: VideoIntent,
        num_titles: int,
        target_platform: str
    ) -> str:
        """构建 Prompt"""
        keywords_text = ', '.join(keywords[:10]) if keywords else '未提供'
        
        return f"""你是短视频标题优化专家。为以下视频生成{num_titles}个不同风格的标题：

【核心内容】
{transcript[:500]}

【关键词】
{keywords_text}

【视频类型】
{intent.category} - {intent.sub_category}

【目标平台】
{target_platform}

请生成 {num_titles} 个标题，每个使用不同风格：
- curiosity_gap (好奇心缺口) - 制造悬念，让人想知道答案
- emotional (情感共鸣) - 激发情感，引发共鸣
- practical (实用价值) - 强调实用性和价值
- controversy (争议讨论) - 制造争议，引发讨论
- benefit (收益承诺) - 承诺具体收益
- fomo (紧迫感) - 制造错失恐惧，强调不看的损失
- celebrity (名人效应) - 借助名人或案例
- number (数字列表) - 用数字吸引眼球

每个标题需包含：
- title: 标题文本 (不超过30字)
- style: 使用的风格
- estimated_ctr: 预估点击率 (0-1)
- rationale: 为什么这个标题有效

返回 JSON:
{{
  "titles": [
    {{
      "title": "他用30天从0学会编程，年薪涨20万！",
      "style": "benefit",
      "estimated_ctr": 0.18,
      "rationale": "承诺具体收益，数字吸引眼球，激发用户学习的欲望"
    }},
    {{
      "title": "30天编程速成，已有10万人学会，你还在等什么？",
      "style": "fomo",
      "estimated_ctr": 0.15,
      "rationale": "制造紧迫感，利用从众心理，促使用户行动"
    }}
  ],
  "best_style_for_platform": "benefit",
  "platform_title_rules": "抖音标题建议简短有力，多用感叹号和数字"
}}

重要：只返回标准 JSON，不要有其他说明文字。"""
    
    def _fallback_titles(self, transcript: str) -> List[Dict]:
        """生成备用标题（当 LLM 不可用时）"""
        # 简单截取转录文本前30字
        fallback_title = transcript[:30].strip()
        if not fallback_title:
            fallback_title = "精彩视频分享"
        
        return [{
            "title": fallback_title,
            "style": "unknown",
            "estimated_ctr": 0.05,
            "rationale": "LLM 不可用，使用转录文本生成"
        }]
    
    def estimate_ctr(
        self,
        title: str,
        style: str
    ) -> float:
        """
        估算标题的点击率
        
        Args:
            title: 标题文本
            style: 标题风格
            
        Returns:
            float: 预估点击率 (0-1)
        """
        # 简化版：基于规则和关键词
        base_ctr = 0.1
        
        # 风格加成
        style_bonus = {
            "benefit": 0.05,
            "curiosity_gap": 0.04,
            "fomo": 0.03,
            "emotional": 0.02,
            "practical": 0.02,
            "controversy": 0.03
        }
        base_ctr += style_bonus.get(style, 0.0)
        
        # 关键词加成
        high_ctr_keywords = ["秒", "天", "倍", "万", "秘籍", "揭秘", "震惊"]
        for keyword in high_ctr_keywords:
            if keyword in title:
                base_ctr += 0.01
        
        # 感叹号加成
        if "！" in title or "!" in title:
            base_ctr += 0.02
        
        # 数字加成
        import re
        if re.search(r'\d+', title):
            base_ctr += 0.02
        
        return min(max(base_ctr, 0.01), 0.3)
    
    def check_platform_compliance(
        self,
        title: str,
        platform: str
    ) -> tuple:
        """
        检查标题是否符合平台规则
        
        Args:
            title: 标题文本
            platform: 平台名称
            
        Returns:
            tuple: (是否合规, 违规原因列表)
        """
        issues = []
        
        # 检查长度
        max_lengths = {
            "douyin": 30,
            "xiaohongshu": 50,
            "weixin": 40
        }
        max_length = max_lengths.get(platform, 30)
        
        if len(title) > max_length:
            issues.append(f"标题超过{max_length}字（当前{len(title)}字）")
        
        # 检查敏感词（简化版）
        sensitive_words = ["最", "第一", "唯一", "国家级", "最高级"]
        for word in sensitive_words:
            if word in title:
                issues.append(f"包含敏感词：{word}")
        
        return (len(issues) == 0, issues)
