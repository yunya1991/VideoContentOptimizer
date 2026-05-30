"""
视频质量评分器
"""

from typing import Dict, List, Optional
from app.models.schema import VideoIntent, QualityScore, VideoMetadata
from app.utils.ai_client import LLMClient
from app.utils.logger import logger
from app.config import get_settings

settings = get_settings()

class QualityScorer:
    """评估视频的内容和制作质量"""
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        初始化质量评分器
        
        Args:
            llm_client: LLM 客户端实例
        """
        self.llm_client = llm_client or self._create_default_client()
    
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
    
    def score_content_quality(
        self,
        transcript: str,
        intent: VideoIntent
    ) -> float:
        """
        评估内容质量 (0-10)
        
        Args:
            transcript: 转录文本
            intent: 视频意图
            
        Returns:
            float: 内容质量评分 (0-10)
        """
        if not self.llm_client:
            return 7.0  # 默认分数
        
        prompt = f"""你是视频内容质量评估专家。评估以下视频内容质量：

【内容】
{transcript[:800]}

【类型】
{intent.category} - {intent.sub_category}

请从以下维度评分 (0-10分):
1. 逻辑性 - 内容是否条理清晰
2. 完整性 - 信息是否完整
3. 原创性 - 内容是否独特
4. 价值性 - 对观众的价值

返回单一数字评分 (0-10)，只返回数字，不要其他内容。"""

        try:
            response = self.llm_client.generate(prompt)
            # 提取数字
            import re
            match = re.search(r'(\d+(\.\d+)?)', response)
            if match:
                score = float(match.group(1))
                return min(max(score, 0.0), 10.0)
        except Exception as e:
            logger.warning(f"内容质量评分失败: {e}")
        
        return 7.0
    
    def score_production_quality(
        self,
        metadata: VideoMetadata,
        visual_features: Optional[List[str]] = None
    ) -> float:
        """
        评估制作质量 (0-10)
        
        Args:
            metadata: 视频元数据
            visual_features: 视觉特征列表
            
        Returns:
            float: 制作质量评分 (0-10)
        """
        # 基于元数据的基础评分
        base_score = 5.0
        
        # 分辨率评分
        try:
            width, height = map(int, metadata.resolution.split('x'))
            if width >= 1920 and height >= 1080:
                resolution_score = 2.0
            elif width >= 1280 and height >= 720:
                resolution_score = 1.5
            else:
                resolution_score = 0.5
        except Exception:
            resolution_score = 0.0
        
        # 帧率评分
        if metadata.fps >= 30:
            fps_score = 1.5
        elif metadata.fps >= 24:
            fps_score = 1.0
        else:
            fps_score = 0.5
        
        # 比特率评分
        if metadata.bitrate >= 3000000:  # 3 Mbps
            bitrate_score = 1.5
        elif metadata.bitrate >= 1500000:  # 1.5 Mbps
            bitrate_score = 1.0
        else:
            bitrate_score = 0.5
        
        total = base_score + resolution_score + fps_score + bitrate_score
        return min(total, 10.0)
    
    def score_engagement_potential(
        self,
        transcript: str,
        intent: VideoIntent
    ) -> float:
        """
        评估互动潜力 (0-10)
        
        Args:
            transcript: 转录文本
            intent: 视频意图
            
        Returns:
            float: 互动潜力评分 (0-10)
        """
        # 基础分数
        base_score = 5.0
        
        # 互动关键词加分
        engagement_keywords = ["点赞", "关注", "评论", "分享", "收藏", "转发", "双击"]
        keyword_count = sum(1 for kw in engagement_keywords if kw in transcript)
        keyword_bonus = min(keyword_count * 1.0, 3.0)
        
        # 情感强度加分
        strong_emotions = ["震撼", "惊讶", "感动", "愤怒", "兴奋", "惊喜"]
        emotion_bonus = 1.0 if any(emotion in transcript for emotion in strong_emotions) else 0.0
        
        # Hook 加分
        hook_bonus = 1.0 if intent.engagement_hooks and len(intent.engagement_hooks) > 0 else 0.0
        
        total = base_score + keyword_bonus + emotion_bonus + hook_bonus
        return min(total, 10.0)
    
    def score_originality(
        self,
        transcript: str,
        intent: VideoIntent
    ) -> float:
        """
        评估原创度 (0-10)
        
        Args:
            transcript: 转录文本
            intent: 视频意图
            
        Returns:
            float: 原创度评分 (0-10)
        """
        # 简化版：基于内容长度和独特性判断
        if len(transcript) < 50:
            return 3.0  # 内容太短，原创度低
        
        # 检查是否有具体案例、数据等
        import re
        has_numbers = bool(re.search(r'\d+', transcript))
        has_specifics = any(word in transcript for word in ["我", "我的", "亲自", "实际"])
        
        base_score = 6.0
        if has_numbers:
            base_score += 1.5
        if has_specifics:
            base_score += 1.5
        
        return min(base_score, 10.0)
    
    def generate_quality_score(
        self,
        transcript: str,
        intent: VideoIntent,
        metadata: VideoMetadata
    ) -> QualityScore:
        """
        生成完整的质量评分
        
        Returns:
            QualityScore: 质量评分对象
        """
        content_quality = self.score_content_quality(transcript, intent)
        production_quality = self.score_production_quality(metadata)
        engagement_potential = self.score_engagement_potential(transcript, intent)
        originality = self.score_originality(transcript, intent)
        
        overall = (content_quality + production_quality + engagement_potential + originality) / 4
        
        improvement_areas = self.generate_recommendations(
            content_quality,
            production_quality,
            engagement_potential,
            originality
        )
        
        return QualityScore(
            content_quality=content_quality,
            production_quality=production_quality,
            engagement_potential=engagement_potential,
            originality=originality,
            overall_score=overall,
            improvement_areas=improvement_areas,
            recommendation=self._generate_overall_recommendation(overall)
        )
    
    def generate_recommendations(
        self,
        content_quality: float,
        production_quality: float,
        engagement_potential: float,
        originality: float
    ) -> List[str]:
        """基于各项评分，生成改进建议"""
        recommendations = []
        
        if content_quality < 6.0:
            recommendations.append("内容质量较低，建议增加信息密度和逻辑性")
        
        if production_quality < 6.0:
            recommendations.append("制作质量有待提升，建议提高分辨率和帧率")
        
        if engagement_potential < 6.0:
            recommendations.append("互动潜力不足，建议增加CTA和互动引导")
        
        if originality < 6.0:
            recommendations.append("原创度较低，建议增加独特的观点和案例")
        
        return recommendations if recommendations else ["整体表现良好，可继续保持"]
    
    def _generate_overall_recommendation(self, overall: float) -> str:
        """生成综合建议"""
        if overall >= 8.0:
            return "整体质量优秀，保持当前创作风格"
        elif overall >= 6.0:
            return "整体质量良好，有提升空间，建议优化薄弱项"
        else:
            return "整体质量需提升，建议重点改善内容和制作质量"
