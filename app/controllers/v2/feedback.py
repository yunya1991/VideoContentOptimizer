"""
API v2 - 用户反馈控制器

将真实用户评分注入进化引擎，使系统越用越智能。
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.main import get_evolution_engine
from app.utils.logger import logger

router = APIRouter(prefix="/feedback", tags=["反馈"])


class FeedbackRequest(BaseModel):
    """用户反馈请求"""
    task_id: str = Field(description="任务 ID（由 analyze/regenerate/optimize 接口返回）")
    score: int = Field(ge=1, le=5, description="用户评分 1-5（1=很差，5=很好）")
    task_type: str = Field(description="任务类型: analyze / regenerate / optimize")
    comment: Optional[str] = Field(None, description="可选文字说明")


def _get_task_data(task_id: str, task_type: str) -> Optional[dict]:
    """
    通过延迟导入直接引用各控制器的模块级 TaskStore 实例。

    延迟导入避免循环依赖（feedback.py → controller → main → feedback），
    同时确保内存后端下共享同一 dict 实例（而非不同实例各自的空 dict）。
    """
    if task_type == "analyze":
        from app.controllers.v2.analyzer import _analysis_tasks
        return _analysis_tasks.get(task_id)
    elif task_type == "regenerate":
        from app.controllers.v2.regenerator import _regen_tasks
        return _regen_tasks.get(task_id)
    elif task_type == "optimize":
        from app.controllers.v2.optimizer import _optimize_tasks
        return _optimize_tasks.get(task_id)
    return None


@router.post("", summary="提交用户反馈")
async def submit_feedback(req: FeedbackRequest):
    """
    提交任务结果的用户反馈，将真实评分注入进化引擎。

    评分归一化规则 (score-1)/4:
    - score=5 → 1.0：优秀，强化当前方案 (capture_success)
    - score=4 → 0.75：良好，强化当前方案 (capture_success)
    - score=3 → 0.5：一般，低权重强化 (capture_success)
    - score=2 → 0.25：较差，记录需改进 (capture_correction)
    - score=1 → 0.0：很差，记录需改进 (capture_correction)

    阈值：normalized >= 0.5（即 score >= 3）→ capture_success；否则 → capture_correction
    """
    if req.task_type not in ("analyze", "regenerate", "optimize"):
        raise HTTPException(
            status_code=400,
            detail=f"不支持的 task_type: '{req.task_type}'，支持: analyze / regenerate / optimize",
        )

    evolution = get_evolution_engine()
    if evolution is None:
        raise HTTPException(status_code=503, detail="进化引擎未初始化，反馈暂时无法记录")

    task_data = _get_task_data(req.task_id, req.task_type)
    if task_data is None:
        raise HTTPException(
            status_code=404,
            detail=f"task_id={req.task_id} 未找到（可能已过期，TTL=1h）",
        )

    ctx = task_data.get("_evolution_context", {})
    normalized = (req.score - 1) / 4.0  # 1→0.0, 2→0.25, 3→0.5, 4→0.75, 5→1.0

    feedback_context: dict = {
        "task_id": req.task_id,
        "user_score": req.score,
        **ctx,
    }
    if req.comment:
        feedback_context["user_comment"] = req.comment

    if normalized >= 0.5:
        evolution.capture_success(
            task_type=ctx.get("task_type", req.task_type),
            context=feedback_context,
            result={"user_score": req.score},
            approach=ctx.get("approach", ""),
            quality_score=normalized,
        )
        action = "capture_success"
        logger.info(
            f"[反馈] 正向信号: task_id={req.task_id} score={req.score} normalized={normalized:.2f}"
        )
    else:
        evolution.capture_correction(
            task_type=ctx.get("task_type", req.task_type),
            original_approach=ctx.get("approach", ""),
            corrected_approach="user_feedback_requested_improvement",
            context=feedback_context,
            reason=req.comment or f"用户评分 {req.score}/5",
        )
        action = "capture_correction"
        logger.info(
            f"[反馈] 负向信号: task_id={req.task_id} score={req.score} normalized={normalized:.2f}"
        )

    return {
        "status": "ok",
        "task_id": req.task_id,
        "normalized_score": round(normalized, 3),
        "action": action,
    }
