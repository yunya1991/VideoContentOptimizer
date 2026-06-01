"""
API v2 - 优化控制器
"""

import uuid
from typing import List, Optional, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.utils.logger import logger
from app.utils.store import TaskStore
from app.models.schema import (
    OptimizationPlan, ScriptOptimization, TitleVariant, VideoIntent,
    SuggestParamsRequest, SuggestParamsResponse, ParamChoiceRecord,
)
from app.services.optimizer.script_optimizer import ScriptOptimizer
from app.services.optimizer.title_generator import TitleGenerator
from app.services.optimizer.param_suggester import ParamSuggester
from app.services.evolution.souls.soul_manager import SoulManager
from app.main import get_evolution_engine

router = APIRouter(prefix="/optimizer", tags=["优化"])

settings = get_settings()

# 优化结果存储（供 /feedback 端点查询进化上下文，TTL=1h 自动清理）
_optimize_tasks = TaskStore("optimize")


# --- 请求/响应模型 ---

class OptimizeRequest(BaseModel):
    """优化请求"""
    transcript: str
    keywords: List[str] = []
    intent: Optional[VideoIntent] = None
    optimization_types: List[str] = ["script", "title"]
    num_variants: int = 3
    target_platform: str = "douyin"

class ScriptOptimizeRequest(BaseModel):
    """文案优化请求"""
    transcript: str
    intent: Optional[VideoIntent] = None
    target_platform: str = "douyin"

class TitleGenerateRequest(BaseModel):
    """标题生成请求"""
    transcript: str
    keywords: List[str] = []
    intent: Optional[VideoIntent] = None
    num_titles: int = 5
    target_platform: str = "douyin"

class OptimizeResponse(BaseModel):
    """优化响应"""
    optimization_id: str
    status: str
    script_result: Optional[Dict] = None
    title_variants: Optional[List[TitleVariant]] = None
    platform_adaptations: Optional[Dict] = None


# --- 接口 ---

@router.post("/optimize", response_model=OptimizeResponse, summary="综合优化")
async def optimize_video(request: OptimizeRequest):
    """
    综合优化视频内容（文案 + 标题 + 平台适配）
    """
    optimization_id = f"opt_{uuid.uuid4().hex[:12]}"

    try:
        intent = request.intent or VideoIntent(
            category="通用", sub_category="", target_audience="", emotion=""
        )

        response = OptimizeResponse(
            optimization_id=optimization_id, status="processing"
        )

        # 文案优化
        if "script" in request.optimization_types:
            optimizer = ScriptOptimizer(evolution_engine=get_evolution_engine())
            result = optimizer.optimize_script(
                original_script=request.transcript,
                intent=intent,
                target_platform=request.target_platform,
            )
            response.script_result = result
            logger.info(f"文案优化完成: {optimization_id}")

        # 标题生成
        if "title" in request.optimization_types:
            generator = TitleGenerator()
            titles = generator.generate_titles(
                transcript=request.transcript,
                keywords=request.keywords,
                intent=intent,
                num_titles=request.num_variants,
                target_platform=request.target_platform,
            )
            response.title_variants = [
                TitleVariant(
                    title=t.get("title", ""),
                    style=t.get("style", "unknown"),
                    estimated_ctr=t.get("estimated_ctr", 0.1),
                    rationale=t.get("rationale"),
                    target_platform=request.target_platform,
                )
                for t in titles
            ]
            logger.info(f"标题生成完成: {optimization_id}, {len(titles)} 个标题")

        response.status = "completed"

        # 存储进化上下文供 /feedback 端点使用（optimization_id 即为 feedback task_id）
        _optimize_tasks.set(optimization_id, {
            "_evolution_context": {
                "task_type": "optimize",
                "context": f"platform={request.target_platform}, transcript_len={len(request.transcript)}",
                "approach": "llm_combined_optimization",
            }
        })

        return response

    except Exception as e:
        logger.error(f"优化失败: {e}")
        raise HTTPException(status_code=500, detail=f"优化失败: {str(e)}")


@router.post("/optimize-script", summary="优化文案")
async def optimize_script(request: ScriptOptimizeRequest):
    """仅优化文案"""
    try:
        intent = request.intent or VideoIntent(
            category="通用", sub_category="", target_audience="", emotion=""
        )

        optimizer = ScriptOptimizer(evolution_engine=get_evolution_engine())
        result = optimizer.optimize_script(
            original_script=request.transcript,
            intent=intent,
            target_platform=request.target_platform,
        )
        logger.info("文案优化完成")

        # 生成 result_id 供 /feedback 端点使用
        result_id = f"opt_{uuid.uuid4().hex[:12]}"
        _optimize_tasks.set(result_id, {
            "_evolution_context": {
                "task_type": "optimize",
                "context": f"platform={request.target_platform}, transcript_len={len(request.transcript)}",
                "approach": "llm_script_optimization",
            }
        })
        result["result_id"] = result_id

        return result

    except Exception as e:
        logger.error(f"文案优化失败: {e}")
        raise HTTPException(status_code=500, detail=f"文案优化失败: {str(e)}")


@router.post("/generate-titles", response_model=List[TitleVariant], summary="生成标题")
async def generate_titles(request: TitleGenerateRequest):
    """生成多个标题变体"""
    try:
        intent = request.intent or VideoIntent(
            category="通用", sub_category="", target_audience="", emotion=""
        )

        generator = TitleGenerator()
        titles = generator.generate_titles(
            transcript=request.transcript,
            keywords=request.keywords,
            intent=intent,
            num_titles=request.num_titles,
            target_platform=request.target_platform,
        )
        logger.info(f"标题生成完成: {len(titles)} 个标题")

        return [
            TitleVariant(
                title=t.get("title", ""),
                style=t.get("style", "unknown"),
                estimated_ctr=t.get("estimated_ctr", 0.1),
                rationale=t.get("rationale"),
                target_platform=request.target_platform,
            )
            for t in titles
        ]

    except Exception as e:
        logger.error(f"标题生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"标题生成失败: {str(e)}")


@router.get("/supported-types", summary="获取支持的优化类型")
async def get_supported_optimization_types():
    """获取支持的优化类型"""
    return {
        "types": [
            {"id": "script", "name": "文案优化", "description": "优化视频文案，提升吸引力"},
            {"id": "title", "name": "标题生成", "description": "生成多风格标题变体"},
            {"id": "platform", "name": "平台适配", "description": "适配不同平台风格 (即将推出)"},
            {"id": "trend", "name": "热度预测", "description": "预测视频热度 (即将推出)"},
        ]
    }


@router.post("/record-param-choice", summary="记录 Step 1 参数选择（进化引擎 + Soul 画像）")
async def record_param_choice(record: ParamChoiceRecord):
    """
    将用户在 Step 1 的参数选择沉淀为进化材料：
    - AI 推荐被接受 → capture_success（quality=0.9）
    - 选了非推荐档案 → capture_success（quality=0.7）
    - 使用参数表单   → capture_correction（学习用户偏好手动控制）
    同时更新 Soul 画像的沟通风格和决策偏好。
    fire-and-forget：前端超时或失败不影响优化主流程。
    """
    soul_changes = []
    try:
        engine = get_evolution_engine()
        platform = record.final_params.target_platform
        goal = record.final_params.optimization_goal
        context = {
            "interaction_mode": record.interaction_mode,
            "chosen_profile": record.chosen_profile_id or "form",
            "platform": platform,
            "goal": goal,
        }

        if engine:
            if record.interaction_mode == "form":
                engine.capture_correction(
                    task_type="param_suggestion",
                    original_approach="ai_recommendation",
                    corrected_approach="manual_form",
                    context=context,
                    reason="用户选择手动配置参数，偏好精细控制",
                )
            elif record.was_ai_recommended:
                engine.capture_success(
                    task_type="param_suggestion",
                    context=context,
                    result=f"profile={record.chosen_profile_id}",
                    approach="ai_recommendation_accepted",
                    quality_score=0.9,
                )
            else:
                engine.capture_success(
                    task_type="param_suggestion",
                    context=context,
                    result=f"profile={record.chosen_profile_id}",
                    approach="ai_recommendation_alternative",
                    quality_score=0.7,
                )
            logger.info(f"进化引擎记录完成: mode={record.interaction_mode}, profile={record.chosen_profile_id}")

        soul_manager = SoulManager()
        result = soul_manager.update_from_param_choice(record)
        soul_changes = result.get("changes", [])
        if soul_changes:
            logger.info(f"Soul 画像更新: {soul_changes}")

    except Exception as e:
        logger.warning(f"record_param_choice 处理异常（不影响主流程）: {e}")

    return {"recorded": True, "soul_changes": soul_changes}


@router.post("/suggest-params", response_model=SuggestParamsResponse, summary="推荐优化参数（询问模式·推荐卡片）")
async def suggest_params(request: SuggestParamsRequest):
    """
    根据视频内容生成 3 个优化方向推荐卡片。
    仅在询问模式下用户选择"推荐卡片"时调用，会额外消耗约 500-1000 tokens。
    LLM 不可用时自动降级为静态默认档案，不会报错。
    """
    try:
        suggester = ParamSuggester()
        result = suggester.suggest(
            transcript=request.transcript,
            keywords=request.keywords,
            intent=request.intent,
        )
        logger.info(f"参数推荐完成，推荐第 {result.default_index} 个档案")
        return result
    except Exception as e:
        logger.error(f"参数推荐失败: {e}")
        raise HTTPException(status_code=500, detail=f"参数推荐失败: {str(e)}")
