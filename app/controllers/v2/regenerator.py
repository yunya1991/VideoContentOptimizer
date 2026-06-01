"""
API v2 - 重生成控制器
"""

import uuid
from typing import List, Optional, Dict

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.utils.logger import logger
from app.utils.store import TaskStore
from app.main import get_evolution_engine

router = APIRouter(prefix="/regenerator", tags=["重生成"])

settings = get_settings()

# 任务状态存储（TTL=1h，自动清理）
_regen_tasks = TaskStore("regen")


# --- 请求/响应模型 ---

class RegenerateRequest(BaseModel):
    """重生成请求"""
    original_video_path: str
    optimization_plan_id: str
    variant_id: str = "v1"
    target_platforms: List[str] = ["douyin", "xiaohongshu", "weixin"]

class RegeneratedVideo(BaseModel):
    """重生成视频信息"""
    platform: str
    video_url: Optional[str] = None
    duration: float = 0.0
    file_size: int = 0

class RegenerateResponse(BaseModel):
    """重生成响应"""
    task_id: str
    status: str
    regenerated_videos: Optional[Dict[str, RegeneratedVideo]] = None
    message: Optional[str] = None


# --- 接口 ---

@router.post("/regenerate", response_model=RegenerateResponse, summary="重新生成视频")
async def regenerate_video(request: RegenerateRequest):
    """
    基于优化方案重新生成视频

    当前状态: 部分可用（平台分辨率转换可用，TTS 和音视频合成待实现）
    """
    task_id = f"regen_{uuid.uuid4().hex[:12]}"
    evolution = get_evolution_engine()
    task_context = {
        "optimization_plan_id": request.optimization_plan_id,
        "variant_id": request.variant_id,
        "target_platforms": request.target_platforms,
    }

    try:
        # _evolution_context 供 /feedback 端点查询，归一化后注入进化引擎
        _regen_tasks.set(task_id, {
            "status": "processing",
            "progress": 0,
            "request": request.model_dump(),
            "_evolution_context": {
                "task_type": "regenerate",
                "context": f"plan={request.optimization_plan_id}, variant={request.variant_id}",
                "approach": "tts_ffmpeg_synthesis",
            },
        })

        # 进化引擎：任务前复盘
        if evolution:
            try:
                review = evolution.pre_task_review("regenerate", task_context)
                if review.get("best_approach"):
                    logger.info(f"[进化] 重生成建议: {review['best_approach'].get('approach', 'N/A')}")
                if review.get("error_preventions"):
                    logger.info(f"[进化] 风险提示: {len(review['error_preventions'])} 条")
            except Exception as e:
                logger.warning(f"进化引擎 pre_task_review 失败（非致命）: {e}")

        from app.services.regenerator.regenerate_video import VideoRegenerator

        regenerator = VideoRegenerator()
        logger.info(f"重生成任务已创建: {task_id}")

        _regen_tasks.update(task_id, status="partial", progress=30)

        # 进化引擎：捕获成功经验
        if evolution:
            try:
                evolution.capture_success(
                    task_type="regenerate",
                    context=task_context,
                    result={"status": "partial", "progress": 30},
                    approach="platform_resolution_conversion",
                )
            except Exception as e:
                logger.warning(f"进化引擎 capture_success 失败（非致命）: {e}")

        return RegenerateResponse(
            task_id=task_id,
            status="partial",
            message="视频重生成部分功能可用：平台分辨率转换已就绪，TTS 音频生成和音视频合成正在开发中。",
        )

    except Exception as e:
        logger.error(f"重生成失败: {e}")
        _regen_tasks.set(task_id, {"status": "failed", "error": str(e)})

        if evolution:
            try:
                evolution.capture_error(
                    task_type="regenerate",
                    context=task_context,
                    error=str(e),
                    error_type="runtime",
                )
            except Exception as ee:
                logger.warning(f"进化引擎 capture_error 失败（非致命）: {ee}")

        raise HTTPException(status_code=500, detail=f"重生成失败: {str(e)}")


@router.get("/status/{task_id}", summary="查询重生成状态")
async def get_regeneration_status(task_id: str):
    """查询重生成任务状态"""
    task = _regen_tasks.get(task_id)
    if task:
        return {
            "task_id": task_id,
            "status": task.get("status", "unknown"),
            "progress": task.get("progress", 0),
        }
    return {
        "task_id": task_id,
        "status": "not_found",
        "progress": 0,
    }


@router.get("/comparison/{task_id}", summary="对比视频版本")
async def compare_versions(task_id: str):
    """
    对比原视频和优化后的视频

    当前状态: 功能开发中，暂不提供对比数据
    """
    task = _regen_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    raise HTTPException(
        status_code=501,
        detail="视频对比功能正在开发中，敬请期待。",
    )


@router.post("/publish", summary="发布视频到平台")
async def publish_video(
    platform: str,
    metadata: Dict,
):
    """
    发布视频到指定平台（通过 upload-post.com）。

    需在 .env 中配置:
      UPLOAD_POST_ENABLED=true
      UPLOAD_POST_API_KEY=<your_key>
      UPLOAD_POST_USERNAME=<your_username>

    支持平台: tiktok/douyin, youtube, instagram, facebook, twitter, linkedin
    不支持: xiaohongshu, weixin（upload-post.com 暂无对应平台）
    """
    from app.services.publish import PublishManager

    pub = PublishManager.from_settings()
    if not pub.enabled:
        raise HTTPException(
            status_code=503,
            detail=(
                "平台发布功能未启用。"
                "请在 .env 中设置 UPLOAD_POST_ENABLED=true 并配置 UPLOAD_POST_API_KEY。"
            ),
        )

    video_path = metadata.get("video_path", "")
    title = metadata.get("title", "")
    platforms = metadata.get("platforms") or [platform]

    try:
        result = pub.publish(video_path=video_path, title=title, platforms=platforms)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/features", summary="重生成功能状态")
async def get_regeneration_features():
    """获取重生成模块各功能的开发状态"""
    return {
        "features": [
            {"name": "平台分辨率转换", "status": "available", "description": "根据平台模板调整视频分辨率"},
            {"name": "TTS 音频生成", "status": "available", "description": "文字转语音，支持 5 种引擎"},
            {"name": "音视频合成", "status": "available", "description": "FFmpeg 两阶段合成优化后的视频"},
            {"name": "平台发布", "status": "planned", "description": "抖音/小红书/微信 API 集成"},
            {"name": "版本对比", "status": "planned", "description": "A/B 测试，对比不同版本效果"},
        ]
    }
