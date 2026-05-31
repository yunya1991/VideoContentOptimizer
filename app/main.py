"""
FastAPI 主应用
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

# 加载配置
settings = get_settings()

# 配置日志
setup_logger(log_level=settings.LOG_LEVEL, log_file=settings.LOG_FILE)

# --- 全局进化引擎实例 ---
evolution_engine = None


def get_evolution_engine():
    """获取全局进化引擎实例（懒加载模式）"""
    global evolution_engine
    if evolution_engine is None:
        try:
            from app.services.evolution.engine import EvolutionEngine
            evolution_engine = EvolutionEngine(project_root=settings.PROJECT_ROOT)
            logger.info("自主进化引擎懒加载初始化成功")
        except Exception as e:
            logger.warning(f"自主进化引擎懒加载初始化失败（非致命）: {e}")
    return evolution_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理 - 启动/关闭时执行"""
    global evolution_engine

    # === 启动 ===
    logger.info("正在初始化自主进化引擎...")
    try:
        from app.services.evolution.engine import EvolutionEngine
        evolution_engine = EvolutionEngine(project_root=settings.PROJECT_ROOT)
        logger.info("自主进化引擎初始化成功")
    except Exception as e:
        logger.warning(f"自主进化引擎初始化失败（非致命）: {e}")
        evolution_engine = None

    yield

    # === 关闭 ===
    logger.info("自主进化引擎正在关闭...")
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
from app.controllers.v2 import analyzer, optimizer, regenerator

app.include_router(analyzer.router, prefix="/api/v2", tags=["分析"])
app.include_router(optimizer.router, prefix="/api/v2", tags=["优化"])
app.include_router(regenerator.router, prefix="/api/v2", tags=["重生成"])


# --- 进化引擎状态端点 ---

@app.get("/evolution/status", summary="进化引擎状态")
async def evolution_status():
    """获取进化引擎运行状态"""
    if evolution_engine is None:
        return {"status": "disabled", "message": "进化引擎未初始化"}
    return {
        "status": "active",
        "project_root": str(evolution_engine.project_root),
        "evolution_dir": str(evolution_engine.evolution_dir),
    }


# --- 基础端点 ---

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
