"""
API v2 - 分析控制器
"""

import os
import uuid
import tempfile
import shutil
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Query

from app.config import get_settings
from app.utils.logger import logger
from app.models.schema import VideoAnalysisResult, VideoMetadata, VideoIntent, QualityScore
from app.services.analyzer.video_parser import VideoParser
from app.services.analyzer.audio_transcriber import AudioTranscriber
from app.services.analyzer.intent_detector import IntentDetector
from app.services.analyzer.quality_scorer import QualityScorer
from app.main import get_evolution_engine

router = APIRouter(prefix="/analyzer", tags=["分析"])

settings = get_settings()

# 内存任务存储（生产环境应替换为 Redis/DB）
_analysis_tasks: dict = {}


# --- 请求/响应模型 ---

from pydantic import BaseModel


class AnalysisResponse(BaseModel):
    """分析响应"""
    task_id: str
    status: str
    filename: Optional[str] = None
    metadata: Optional[VideoMetadata] = None
    transcript: Optional[str] = None
    intent: Optional[VideoIntent] = None
    quality_score: Optional[QualityScore] = None


# --- 安全工具函数 ---

def _sanitize_filename(filename: str) -> str:
    """清洗文件名，防止路径穿越"""
    safe_name = os.path.basename(filename)
    name, ext = os.path.splitext(safe_name)
    # 只保留字母数字、连字符、下划线
    safe_name = "".join(c for c in name if c.isalnum() or c in "-_")
    if not safe_name:
        safe_name = "upload"
    return safe_name + ext.lower()


def _validate_extension(filename: str) -> str:
    """校验文件扩展名"""
    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    allowed = settings.ALLOWED_EXTENSIONS
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式 '.{ext}'，支持: {', '.join(allowed)}",
        )
    return ext


def _save_upload(file: UploadFile) -> str:
    """安全地保存上传文件到临时目录，返回路径"""
    safe_name = _sanitize_filename(file.filename or "video.mp4")
    _validate_extension(safe_name)

    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, unique_name)

    # 文件大小校验
    max_bytes = settings.MAX_VIDEO_SIZE_MB * 1024 * 1024
    total_size = 0

    with open(temp_path, "wb") as buffer:
        while chunk := file.file.read(1024 * 1024):  # 1MB 分块读取
            total_size += len(chunk)
            if total_size > max_bytes:
                buffer.close()
                os.remove(temp_path)
                raise HTTPException(
                    status_code=413,
                    detail=f"文件过大，最大允许 {settings.MAX_VIDEO_SIZE_MB} MB",
                )
            buffer.write(chunk)

    logger.info(f"文件已保存: {temp_path} ({total_size} bytes)")
    return temp_path


def _cleanup(path: str):
    """安全清理临时文件"""
    try:
        if path and os.path.isfile(path):
            os.remove(path)
    except OSError as e:
        logger.warning(f"清理临时文件失败 {path}: {e}")


# --- 接口 ---

@router.post("/analyze", response_model=AnalysisResponse, summary="分析单个视频")
async def analyze_video(
    video: UploadFile = File(..., description="视频文件 (mp4, mov, avi, mkv)"),
    extract_keywords: bool = Query(True, description="是否提取关键词"),
    predict_trend: bool = Query(True, description="是否预测热度"),
):
    """上传并分析视频，返回元数据、转录、意图识别和质量评分"""
    temp_path = None
    task_id = f"task_{uuid.uuid4().hex[:12]}"

    try:
        # 1. 安全保存文件
        temp_path = _save_upload(video)

        # 进化引擎：任务前复盘
        evolution = get_evolution_engine()
        task_context = {"filename": video.filename, "task_id": task_id}
        if evolution:
            try:
                review = evolution.pre_task_review("analyze", task_context)
                if review.get("best_approach"):
                    logger.info(f"[进化] 分析建议: {review['best_approach'].get('approach', 'N/A')}")
                if review.get("error_preventions"):
                    logger.info(f"[进化] 风险提示: {len(review['error_preventions'])} 条")
            except Exception as e:
                logger.warning(f"进化引擎 pre_task_review 失败（非致命）: {e}")

        # 2. 视频元数据解析
        parser = VideoParser()
        metadata = parser.parse_video(temp_path)
        logger.info(f"元数据解析完成: {metadata.duration:.1f}s, {metadata.resolution}")

        # 3. 音频转录
        transcript = None
        if settings.ENABLE_AUDIO_TRANSCRIPTION:
            try:
                transcriber = AudioTranscriber()
                transcript = transcriber.transcribe(temp_path)
                logger.info(f"转录完成: {len(transcript)} 字符")
            except Exception as e:
                logger.warning(f"转录失败 (非致命): {e}")

        # 4. 意图识别
        intent = None
        if transcript:
            try:
                detector = IntentDetector()
                intent = detector.detect_intent(transcript)
                logger.info(f"意图识别: {intent.category}")
            except Exception as e:
                logger.warning(f"意图识别失败 (非致命): {e}")

        # 5. 质量评分
        quality = None
        try:
            scorer = QualityScorer()
            quality = scorer.score_production_quality(metadata)
            logger.info(f"质量评分: 制作 {quality.production_quality:.1f}")
        except Exception as e:
            logger.warning(f"质量评分失败 (非致命): {e}")

        # 6. 构建响应
        response = AnalysisResponse(
            task_id=task_id,
            status="completed",
            filename=video.filename,
            metadata=metadata,
            transcript=(
                transcript[:500] + "..."
                if transcript and len(transcript) > 500
                else transcript
            ),
            intent=intent,
            quality_score=quality,
        )

        # 缓存结果
        _analysis_tasks[task_id] = response.model_dump()

        # 进化引擎：捕获成功经验
        if evolution:
            try:
                quality_val = quality.production_quality / 100.0 if quality else 0.5
                quality_val = max(0.0, min(1.0, quality_val))
                evolution.capture_success(
                    task_type="analyze",
                    context=task_context,
                    result={"status": "completed", "has_transcript": transcript is not None},
                    approach="full_pipeline",
                    quality_score=quality_val,
                )
            except Exception as e:
                logger.warning(f"进化引擎 capture_success 失败（非致命）: {e}")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分析失败: {e}")
        
        # 进化引擎：捕获错误经验
        if evolution:
            try:
                evolution.capture_error(
                    task_type="analyze",
                    context=task_context,
                    error=str(e),
                    error_type="runtime",
                )
            except Exception as ee:
                logger.warning(f"进化引擎 capture_error 失败（非致命）: {ee}")
        
        raise HTTPException(status_code=500, detail=f"视频分析失败: {str(e)}")
    finally:
        _cleanup(temp_path)


@router.post("/batch", summary="批量分析视频")
async def batch_analyze(
    videos: List[UploadFile] = File(..., description="视频文件列表"),
):
    """批量分析视频"""
    if len(videos) > settings.MAX_BATCH_VIDEOS:
        raise HTTPException(
            status_code=400,
            detail=f"批量上传数量超限，最多 {settings.MAX_BATCH_VIDEOS} 个",
        )

    results = []
    for video in videos:
        temp_path = None
        try:
            temp_path = _save_upload(video)
            parser = VideoParser()
            metadata = parser.parse_video(temp_path)

            results.append({
                "filename": video.filename,
                "status": "success",
                "duration": metadata.duration,
                "resolution": metadata.resolution,
                "file_size": metadata.file_size,
            })
        except HTTPException as e:
            results.append({
                "filename": video.filename,
                "status": "error",
                "error": e.detail,
            })
        except Exception as e:
            logger.error(f"批量分析单个文件失败 {video.filename}: {e}")
            results.append({
                "filename": video.filename,
                "status": "error",
                "error": str(e),
            })
        finally:
            _cleanup(temp_path)

    batch_id = f"batch_{uuid.uuid4().hex[:12]}"
    logger.info(f"批量分析完成: {batch_id}, 成功 {sum(1 for r in results if r['status'] == 'success')}/{len(videos)}")

    return {
        "batch_id": batch_id,
        "total": len(videos),
        "processed": len([r for r in results if r["status"] == "success"]),
        "results": results,
    }


@router.get("/result/{task_id}", summary="获取分析结果")
async def get_analysis_result(task_id: str):
    """获取缓存的分析结果"""
    result = _analysis_tasks.get(task_id)
    if result:
        return {"task_id": task_id, "status": "completed", "result": result}
    return {"task_id": task_id, "status": "not_found", "result": None}


@router.get("/supported-formats", summary="获取支持的格式")
async def get_supported_formats():
    """获取支持的视频格式"""
    return {
        "formats": settings.ALLOWED_EXTENSIONS,
        "max_size_mb": settings.MAX_VIDEO_SIZE_MB,
    }
