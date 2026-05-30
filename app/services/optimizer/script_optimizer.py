"""
文案优化器（基于 LLM）
"""

from typing import Dict, List, Optional
from app.models.schema import VideoIntent
from app.utils.ai_client import LLMClient
from app.config import get_settings

settings = get_settings()

class ScriptOptimizer:
    """优化视频文案以提高吸引力和可读性"""
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        初始化文案优化器
        
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
            print(f"创建 LLM 客户端失败: {e}")
            return None
    
    def optimize_script(
        self,
        original_script: str,
        intent: VideoIntent,
        target_platform: str = "douyin"
    ) -> Dict:
        """
        优化文案
        
        Args:
            original_script: 原文案
            intent: 视频意图
            target_platform: 目标平台
            
        Returns:
            Dict: 包含优化结果的字典
        """
        if not self.llm_client:
            return {
                "optimized_script": original_script,
                "changes": ["未提供 LLM 客户端，无法优化"],
                "readability_improvement": 0.0,
                "engagement_increase": 0.0
            }
        
        prompt = self._build_optimization_prompt(
            original_script,
            intent,
            target_platform
        )
        
        try:
            result = self.llm_client.generate_json(prompt)
            return self._parse_optimization_result(result, original_script)
        except Exception as e:
            print(f"文案优化失败: {e}")
            return {
                "optimized_script": original_script,
                "changes": [f"优化失败: {str(e)}"],
                "readability_improvement": 0.0,
                "engagement_increase": 0.0
            }
    
    def _build_optimization_prompt(
        self,
        original_script: str,
        intent: VideoIntent,
        target_platform: str
    ) -> str:
        """构建优化 Prompt"""
        return f"""你是短视频文案优化专家。分析并优化下列视频文案：

【原文案】
{original_script}

【视频类型】
{intent.category} - {intent.sub_category}

【目标平台】
{target_platform}

【目标受众】
{intent.target_audience}

【情感基调】
{intent.emotion}

请优化文案，使其具备以下特点：
1. 前5秒就能吸引用户 (Hook机制)
2. 信息密度合理，节奏感强
3. 有明确的 CTA (行动号召)
4. 符合{target_platform}平台用语习惯
5. 增加情感共鸣，引发互动

优化维度详解：
- Hook: 开头要有悬念、疑问、惊喜或痛点
- 节奏: 每15-20秒一个小高潮
- CTA: 结尾引导点赞、关注、评论、分享
- 平台化: 使用平台流行语和表达方式
- 情感: 激发用户情绪，促使其互动

返回 JSON:
{{
  "optimized_script": "优化后的完整文案，保留原意但更具吸引力",
  "changes": [
    "改进点1: 原开头较平淡，改为疑问式开头增加悬念",
    "改进点2: 中段增加情感共鸣点，引发用户认同",
    "改进点3: 结尾增加明确的CTA，引导用户互动"
  ],
  "readability_improvement": 15,
  "engagement_increase": 20,
  "hook_strength_before": 5.0,
  "hook_strength_after": 8.5,
  "cta_effectiveness": "strong"
}}

重要：只返回标准 JSON，不要有其他说明文字。"""
    
    def _parse_optimization_result(
        self,
        result: Dict,
        original_script: str
    ) -> Dict:
        """解析优化结果"""
        return {
            "optimized_script": result.get("optimized_script", original_script),
            "changes": result.get("changes", []),
            "readability_improvement": result.get("readability_improvement", 0.0),
            "engagement_increase": result.get("engagement_increase", 0.0),
            "hook_strength_before": result.get("hook_strength_before"),
            "hook_strength_after": result.get("hook_strength_after"),
            "cta_effectiveness": result.get("cta_effectiveness")
        }
    
    def optimize_for_platform(
        self,
        script: str,
        platform: str,
        intent: Optional[VideoIntent] = None
    ) -> str:
        """
        针对特定平台优化文案
        
        Args:
            script: 原文案
            platform: 平台名称
            intent: 视频意图（可选）
            
        Returns:
            str: 优化后的文案
        """
        if not self.llm_client:
            return script
        
        prompt = f"""你是短视频文案优化专家。将以下文案优化为{platform}平台风格：

【原文案】
{script}

【平台特点】
{self._get_platform_style(platform)}

请优化文案，使其符合{platform}平台的语言风格和节奏特点。
只返回优化后的文案，不要其他说明。"""

        try:
            return self.llm_client.generate(prompt).strip()
        except Exception as e:
            print(f"平台优化失败: {e}")
            return script
    
    def _get_platform_style(self, platform: str) -> str:
        """获取平台风格说明"""
        styles = {
            "douyin": """
                - 语言简短有力，多用口语化表达
                - 喜欢用感叹号、疑问句
                - 节奏快，信息密度高
                - 多用热门话题和流行语
            """,
            "xiaohongshu": """
                - 语气亲切，像朋友分享
                - 注重实用价值和干货
                - 多用表情符号增加亲和力
                - 标题和开头要吸引人
            """,
            "weixin": """
                - 语言自然，不过度营销
                - 注重真实感和温度
                - 适合熟人社交传播
                - 引导转发到朋友圈
            """
        }
        return styles.get(platform, "通用风格")
    
    def generate_multiple_versions(
        self,
        original_script: str,
        intent: VideoIntent,
        num_versions: int = 3
    ) -> List[Dict]:
        """
        生成多个优化版本
        
        Args:
            original_script: 原文案
            intent: 视频意图
            num_versions: 版本数量
            
        Returns:
            List[Dict]: 优化版本列表
        """
        versions = []
        for i in range(num_versions):
            # 可以添加不同的优化策略
            version = self.optimize_script(
                original_script=original_script,
                intent=intent,
                target_platform="douyin"  # 可以轮换平台
            )
            version["version_id"] = f"v{i+1}"
            versions.append(version)
        
        return versions
