"""
API v2 - 分析控制器
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import tempfile
import shutil

from app.config import get_settings
from app.models.schema import VideoAnalysisResult, VideoMetadata, VideoIntent, QualityScore
from app.services.analyzer.video_parser import VideoParser
from app.services.analyzer.audio_transcriber import AudioTranscriber
from app.services.analyzer.intent_detector import IntentDetector
from app.services.analyzer.quality_scorer import QualityScorer

router = APIRouter(prefix="/analyzer", tags=["分析"])

settings = get_settings()
TEMP_DIR = tempfile.gettempdir()

# --- 请求/响应模型 ---

class AnalyzeRequest(BaseModel):
    """分析请求"""
    video_path: str
    extract_keywords: bool = True
    predict_trend: bool = True

class AnalysisResponse(BaseModel):
    """分析响应"""
    task_id: str
    status: str
    metadata: Optional[VideoMetadata] = None
    transcript: Optional[str] = None
    intent: Optional[VideoIntent] = None
    quality_score: Optional[QualityScore] = None
    estimated_time: int = 30

# --- 接口 ---

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_video(
    video: UploadFile = File(...),
    extract_keywords: bool = True,
    predict_trend: bool = True
):
    """
    分析单个视频
    
    - **video**: 视频文件 (mp4, mov, avi, mkv)
    - **extract_keywords**: 是否提取关键词
    - **predict_trend**: 是否预测热度
    """
    temp_path = None
    try:
        # 保存上传的文件
        temp_path = os.path.join(TEMP_DIR, video.filename)
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(video.file, buffer)
        
        # 分析视频
        parser = VideoParser()
        metadata = parser.parse_video(temp_path)
        
        # 创建响应
        response = AnalysisResponse(
            task_id=f"task_{hash(temp_path) % 100000}",
            status="processing"
        )
        
        # 转录音频（异步任务中完成）
        transcript = None
        if settings.ENABLE_AUDIO_TRANSCRIPTION:
            try:
                transcriber = AudioTranscriber()
                transcript = transcriber.transcribe(temp_path)
                response.transcript = transcript[:500] + "..." if transcript and len(transcript) > 500 else transcript
            except Exception as e:
                print(f"转录失败: {e}")
        
        response.metadata = metadata
        response.status = "completed"
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 清理临时文件
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass

@router.post("/batch", summary="批量分析")
async def batch_analyze(videos: List[UploadFile] = File(...)):
    """
    批量分析视频
    """
    results = []
    
    for video in videos:
        temp_path = None
        try:
            temp_path = os.path.join(TEMP_DIR, video.filename)
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(video.file, buffer)
            
            parser = VideoParser()
            metadata = parser.parse_video(temp_path)
            
            results.append({
                "filename": video.filename,
                "status": "success",
                "duration": metadata.duration,
                "resolution": metadata.resolution
            })
            
        except Exception as e:
            results.append({
                "filename": video.filename,
                "status": "error",
                "error": str(e)
            })
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
    
    return {
        "batch_id": "batch_12345",
        "total": len(videos),
        "processed": len([r for r in results if r["status"] == "success"]),
        "results": results
    }

@router.get("/result/{task_id}")
async def get_analysis_result(task_id: str):
    """
    获取分析结果
    """
    # TODO: 从数据库或缓存中获取结果
    return {
        "task_id": task_id,
        "status": "completed",
        "result": {}
    }

@router.get("/supported-formats")
async def get_supported_formats():
    """获取支持的视频格式"""
    return {
        "formats": ["mp4", "mov", "avi", "mkv", "flv", "wmv"],
        "max_size_mb": settings.MAX_VIDEO_SIZE_MB
    }
