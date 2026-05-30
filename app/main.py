"""
FastAPI 主应用
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import shutil
import os
import tempfile

from app.config import get_settings
from app.services.analyzer.video_parser import VideoParser
from app.services.analyzer.audio_transcriber import AudioTranscriber

# 创建 FastAPI 应用
app = FastAPI(
    title="Video AI Optimizer API",
    description="视频智能分析与优化 API",
    version="2.0.0"
)

# CORS 配置
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 临时存储目录
TEMP_DIR = tempfile.gettempdir()

@app.get("/")
async def root():
    """API 根路径"""
    return {
        "name": "Video AI Optimizer API",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "analyzer": "/api/v2/analyzer",
            "optimizer": "/api/v2/optimizer",
            "regenerator": "/api/v2/regenerator",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}

@app.post("/api/v2/analyze", summary="分析单个视频")
async def analyze_video(
    video: UploadFile = File(...),
    extract_keywords: bool = True,
    predict_trend: bool = True
):
    """
    上传并分析视频
    
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
        
        # 分析视频元数据
        parser = VideoParser()
        metadata = parser.parse_video(temp_path)
        
        # 转录音频
        transcript = None
        try:
            if settings.ENABLE_AUDIO_TRANSCRIPTION:
                transcriber = AudioTranscriber()
                transcript = transcriber.transcribe(temp_path)
        except Exception as e:
            print(f"转录失败: {e}")
        
        # 返回结果
        return {
            "status": "success",
            "filename": video.filename,
            "metadata": {
                "duration": metadata.duration,
                "fps": metadata.fps,
                "resolution": metadata.resolution,
                "format": metadata.format,
                "file_size": metadata.file_size
            },
            "transcript": transcript[:500] + "..." if transcript and len(transcript) > 500 else transcript
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 清理临时文件
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass

@app.post("/api/v2/batch/analyze", summary="批量分析视频")
async def batch_analyze(
    videos: List[UploadFile] = File(...),
    parallel_workers: int = 4
):
    """
    批量分析视频
    
    - **videos**: 视频文件列表
    - **parallel_workers**: 并行工作线程数
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
                "resolution": metadata.resolution,
                "file_size": metadata.file_size
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
        "total": len(videos),
        "processed": len([r for r in results if r["status"] == "success"]),
        "results": results
    }

# 注册路由（如果控制器存在）
# from app.controllers.v2 import analyzer, optimizer, regenerator
# app.include_router(analyzer.router, prefix="/api/v2/analyzer", tags=["分析"])
# app.include_router(optimizer.router, prefix="/api/v2/optimizer", tags=["优化"])
# app.include_router(regenerator.router, prefix="/api/v2/regenerator", tags=["重生成"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        debug=settings.API_DEBUG
    )
