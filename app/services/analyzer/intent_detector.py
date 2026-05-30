"""
视频意图识别器（基于 LLM）
"""

import json
from typing import List, Optional
from app.models.schema import VideoIntent
from app.utils.ai_client import LLMClient
from app.config import get_settings

settings = get_settings()

class IntentDetector:
    """使用大模型识别视频的核心意图"""
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        初始化意图识别器
        
        Args:
            llm_client: LLM 客户端实例（如果为 None，则自动创建）
        """
        self.llm_client = llm_client or self._create_default_client()
    
    def _create_default_client(self) -> LLMClient:
        """创建默认的 LLM 客户端"""
        if not settings.LLM_API_KEY:
            return None
        
        return LLMClient(
            provider=settings.LLM_PROVIDER,
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
            model=settings.LLM_MODEL
        )
    
    def detect_intent(
        self,
        transcript: str,
        visual_features: Optional[List[str]] = None,
        title: str = ""
    ) -> VideoIntent:
        """
        识别视频意图
        
        Args:
            transcript: 音频转录文本
            visual_features: 视觉特征列表（可选）
            title: 视频标题（可选）
            
        Returns:
            VideoIntent: 视频意图对象
        """
        if not self.llm_client:
            return self._default_intent()
        
        prompt = self._build_prompt(transcript, visual_features, title)
        
        try:
            result = self.llm_client.generate_json(prompt)
            return self._parse_result(result)
        except Exception as e:
            print(f"意图识别失败: {e}")
            return self._default_intent()
    
    def _build_prompt(
        self,
        transcript: str,
        visual_features: Optional[List[str]],
        title: str
    ) -> str:
        """构建 Prompt"""
        visual_text = ', '.join(visual_features) if visual_features else '未提供'
        
        return f"""你是短视频内容分类专家。分析以下视频内容，识别其核心意图：

【音频转录】
{transcript[:1000]}

【视觉特征】
{visual_text}

【视频标题】
{title if title else '未提供'}

请识别视频的核心意图并返回 JSON:
{{
  "category": "教育/娱乐/知识分享/生活分享/产品推荐/创意展示/美食/旅游/运动/其他",
  "sub_category": "具体子类别，如编程教学、美食教程等",
  "target_audience": "目标受众描述，如18-35岁职场人士、宝妈等",
  "emotion": "情感基调，如励志、幽默、严肃、温暖、激动等",
  "core_message": "核心信息，用一句话概括视频要传达的主要内容",
  "engagement_hooks": ["吸引点1", "吸引点2", "吸引点3"],
  "value_proposition": "价值主张，用户为什么要看完这个视频",
  "confidence": 0.85
}}

重要：只返回标准 JSON，不要有任何其他说明文字。"""
    
    def _parse_result(self, result: dict) -> VideoIntent:
        """解析 LLM 返回的结果"""
        return VideoIntent(
            category=result.get("category", "未知"),
            sub_category=result.get("sub_category", ""),
            target_audience=result.get("target_audience", ""),
            emotion=result.get("emotion", ""),
            core_message=result.get("core_message", ""),
            confidence=result.get("confidence", 0.5),
            engagement_hooks=result.get("engagement_hooks", []),
            value_proposition=result.get("value_proposition")
        )
    
    def _default_intent(self) -> VideoIntent:
        """返回默认的意图（当 LLM 不可用时）"""
        return VideoIntent(
            category="未知",
            sub_category="",
            target_audience="",
            emotion="",
            core_message="",
            confidence=0.0
        )
    
    def batch_detect(
        self,
        transcripts: List[str],
        visual_features_list: Optional[List[List[str]]] = None,
        titles: Optional[List[str]] = None
    ) -> List[VideoIntent]:
        """
        批量识别意图
        
        Args:
            transcripts: 转录文本列表
            visual_features_list: 视觉特征列表的列表
            titles: 标题列表
            
        Returns:
            List[VideoIntent]: 意图列表
        """
        results = []
        for i, transcript in enumerate(transcripts):
            visual_features = None
            title = ""
            
            if visual_features_list and i < len(visual_features_list):
                visual_features = visual_features_list[i]
            
            if titles and i < len(titles):
                title = titles[i]
            
            intent = self.detect_intent(transcript, visual_features, title)
            results.append(intent)
        
        return results
