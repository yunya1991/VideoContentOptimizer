"""
数据模型定义 (Pydantic)
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# ==================== 视频元数据 ====================

class VideoMetadata(BaseModel):
    """视频基础元数据"""
    duration: float = Field(..., description="时长(秒)")
    fps: int = Field(..., description="帧率")
    resolution: str = Field(..., description="分辨率，如 '1920x1080'")
    bitrate: int = Field(..., description="比特率")
    format: str = Field(..., description="视频格式")
    file_size: Optional[int] = Field(None, description="文件大小(字节)")

# ==================== 视频意图 ====================

class VideoIntent(BaseModel):
    """视频意图分类结果"""
    category: str = Field(..., description="类别：教育/娱乐/知识分享等")
    sub_category: str = Field("", description="子类别")
    target_audience: str = Field("", description="目标受众")
    emotion: str = Field("", description="情感基调")
    core_message: str = Field("", description="核心信息")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="置信度 (0-1)")
    engagement_hooks: Optional[List[str]] = Field(default_factory=list, description="吸引点")
    value_proposition: Optional[str] = Field(None, description="价值主张")

# ==================== 质量评分 ====================

class QualityScore(BaseModel):
    """视频质量评分"""
    content_quality: float = Field(..., ge=0.0, le=10.0, description="内容质量 (0-10)")
    production_quality: float = Field(..., ge=0.0, le=10.0, description="制作质量 (0-10)")
    engagement_potential: float = Field(..., ge=0.0, le=10.0, description="互动潜力 (0-10)")
    originality: float = Field(..., ge=0.0, le=10.0, description="原创度 (0-10)")
    overall_score: Optional[float] = Field(None, description="综合评分")
    improvement_areas: Optional[List[str]] = Field(default_factory=list, description="改进方向")
    recommendation: Optional[str] = Field(None, description="综合建议")

# ==================== 平台分析 ====================

class PlatformScore(BaseModel):
    """单平台评分"""
    platform: str
    score: float = Field(..., ge=0.0, le=100.0, description="平台适配评分 (0-100)")
    reasons: Optional[List[str]] = None

class PlatformAnalysis(BaseModel):
    """平台适配分析"""
    best_platform: str = Field(..., description="最佳平台")
    platform_scores: List[PlatformScore] = Field(default_factory=list)
    estimated_reach: Optional[int] = Field(None, description="预估触达")
    peak_hours: Optional[List[str]] = Field(default_factory=list, description="发布最佳时段")

# ==================== 关键词 ====================

class KeywordInfo(BaseModel):
    """关键词信息"""
    keyword: str
    frequency: int = Field(0, description="出现频率")
    relevance: float = Field(0.0, ge=0.0, le=1.0, description="相关度 (0-1)")
    search_volume: Optional[int] = Field(None, description="搜索热度")
    type: Optional[str] = Field(None, description="关键词类型：core/longtail/hashtag")

# ==================== 趋势预测 ====================

class TrendPrediction(BaseModel):
    """热度趋势预测"""
    trend_score: float = Field(..., ge=0.0, le=100.0, description="热度评分 (0-100)")
    growth_potential: str = Field(..., description="增长潜力：high/medium/low")
    similar_viral_videos: Optional[List[str]] = Field(default_factory=list)
    days_to_peak: Optional[int] = Field(None, description="预计达到高峰天数")
    recommendation: Optional[str] = Field(None, description="发布建议")

# ==================== 分析结果 ====================

class VideoAnalysisResult(BaseModel):
    """视频内容分析的完整结果"""
    task_id: str
    video_path: str
    upload_time: datetime = Field(default_factory=datetime.now)
    
    # 元数据
    video_metadata: VideoMetadata
    
    # 内容分析
    audio_transcript: str = ""
    text_detected: Optional[str] = None
    
    # 意图识别
    video_intent: VideoIntent
    
    # 质量评估
    quality_score: QualityScore
    
    # 平台分析
    platform_analysis: PlatformAnalysis
    
    # 关键词提取
    extracted_keywords: List[KeywordInfo] = Field(default_factory=list)
    
    # 趋势预测
    trend_prediction: TrendPrediction
    
    # 改进建议
    improvement_opportunities: Optional[List[Dict]] = Field(default_factory=list)

# ==================== 优化方案 ====================

class TitleVariant(BaseModel):
    """标题变体"""
    title: str
    style: str = Field(..., description="标题风格")
    estimated_ctr: float = Field(..., ge=0.0, le=1.0, description="预估点击率")
    target_platform: Optional[str] = None
    rationale: Optional[str] = None

class ScriptOptimization(BaseModel):
    """文案优化结果"""
    original_script: str
    optimized_script: str
    optimization_reasons: List[str] = Field(default_factory=list)
    readability_before: Optional[float] = None
    readability_after: Optional[float] = None
    improvement_percentage: float = 0.0

class CreativeVariant(BaseModel):
    """创意变体"""
    variant_id: str
    hook_type: str
    thumbnail_suggestion: Optional[str] = None
    description: str = ""
    estimated_engagement: float = Field(..., ge=0.0, le=1.0)

class PublishingStrategy(BaseModel):
    """发布策略"""
    recommended_platforms: List[str] = Field(default_factory=list)
    optimal_posting_time: str = ""
    hashtag_strategy: List[str] = Field(default_factory=list)
    caption_versions: List[str] = Field(default_factory=list)
    cross_platform_plan: Optional[Dict] = None

class OptimizationPlan(BaseModel):
    """AI 生成的优化方案"""
    analysis_id: str
    
    # 文案优化
    script_optimization: Optional[ScriptOptimization] = None
    
    # 标题优化
    title_variants: List[TitleVariant] = Field(default_factory=list)
    
    # 平台适配
    platform_adaptations: Dict = Field(default_factory=dict)
    
    # 多版本方案
    creative_variants: List[CreativeVariant] = Field(default_factory=list)
    
    # 发布策略
    publishing_strategy: Optional[PublishingStrategy] = None
    
    # 预期效果
    expected_metrics: Optional[Dict] = None

# ==================== 批处理 ====================

class BatchAnalysisTask(BaseModel):
    """批量分析任务"""
    task_id: str
    user_id: str = "default"
    
    # 任务配置
    videos: List[Dict] = Field(default_factory=list)
    task_config: Dict = Field(default_factory=dict)
    
    # 任务进度
    status: str = "pending"  # pending, processing, completed, failed
    progress: float = Field(0.0, ge=0.0, le=100.0)
    
    # 结果
    results: Optional[List[VideoAnalysisResult]] = None
    plans: Optional[List[OptimizationPlan]] = None
    
    # 统计信息
    statistics: Optional[Dict] = None
