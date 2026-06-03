"""
FastAPI 应用
"""

import os
import uuid
import tempfile
import shutil
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.utils.logger import setup_logger, logger
from app.services.evolution.souls.soul_manager import SoulManager

# 全局配置
settings = get_settings()

# 初始化日志
setup_logger(log_level=settings.LOG_LEVEL, log_file=settings.LOG_FILE)

# --- 全局进化引擎实例 ---
evolution_engine = None


def get_evolution_engine():
    """获取全局进化引擎实例（惰性初始化模式）"""
    global evolution_engine
    if evolution_engine is None:
        try:
            from app.services.evolution.engine import EvolutionEngine
            evolution_engine = EvolutionEngine(project_root=settings.PROJECT_ROOT)
            logger.info("进化引擎惰性初始化成功")
        except Exception as e:
            logger.warning(f"进化引擎惰性初始化失败，已禁用: {e}")
    return evolution_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理 - 启动/关闭时执行"""
    global evolution_engine

    # === 启动 ===
    logger.info("正在初始化进化引擎系统...")
    try:
        from app.services.evolution.engine import EvolutionEngine
        evolution_engine = EvolutionEngine(project_root=settings.PROJECT_ROOT)
        logger.info("进化引擎初始化成功")
    except Exception as e:
        logger.warning(f"进化引擎初始化失败，已禁用: {e}")
        evolution_engine = None

    yield

    # === 关闭 ===
    logger.info("进化引擎系统正在关闭...")
    evolution_engine = None
    logger.info("应用已关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title="Video AI Optimizer API",
    description="视频智能分析与优化 API",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 注册 v2 路由 ---
from app.controllers.v2 import analyzer, optimizer, regenerator, feedback

app.include_router(analyzer.router, prefix="/api/v2", tags=["分析"])
app.include_router(optimizer.router, prefix="/api/v2", tags=["优化"])
app.include_router(regenerator.router, prefix="/api/v2", tags=["重生成"])
app.include_router(feedback.router, prefix="/api/v2", tags=["反馈"])


# --- 进化引擎状态端点 ---

@app.get("/evolution/status", summary="进化引擎状态")
async def evolution_status():
    """获取进化引擎系统状态"""
    if evolution_engine is None:
        return {"status": "disabled", "message": "进化引擎未初始化"}
    return {
        "status": "active",
        "project_root": str(evolution_engine.project_root),
        "evolution_dir": str(evolution_engine.evolution_dir),
    }


@app.get("/evolution/soul/status", summary="Soul 状态")
async def soul_status(soul_id: str = "default"):
    """获取 Soul 状态信息

    Args:
        soul_id: Soul ID，默认为 'default'

    Returns:
        Soul 状态摘要，包含等级、经验值、对话历史等
    """
    try:
        soul_manager = SoulManager()
        status = soul_manager.get_soul_status(soul_id=soul_id)
        return {"status": "active", **status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取 Soul 状态失败: {str(e)}")


# --- 基础端点 ---

@app.get("/")
async def root():
    """API 根路由"""
    return {
        "name": "Video AI Optimizer API",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "analyzer": "/api/v2/analyzer",
            "optimizer": "/api/v2/optimizer",
            "regenerator": "/api/v2/regenerator",
            "feedback": "/api/v2/feedback",
            "docs": "/docs",
            "redoc": "/redoc",
        },
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


# --- 启动入口 ---

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level=settings.LOG_LEVEL.lower(),
    )
