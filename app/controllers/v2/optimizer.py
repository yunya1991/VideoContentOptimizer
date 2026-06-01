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
)
from app.services.optimizer.script_optimizer import ScriptOptimizer
from app.services.optimizer.title_generator import TitleGenerator
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
