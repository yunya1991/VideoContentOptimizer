"""
FastAPI 主应用
"""

import os
import uuid
import tempfile
import shutil
from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.utils.logger import setup_logger, logger

# 加载配置
settings = get_settings()

# 配置日志
setup_logger(log_level=settings.LOG_LEVEL, log_file=settings.LOG_FILE)

# 创建 FastAPI 应用
app = FastAPI(
    title="Video AI Optimizer API",
    description="视频智能分析与优化 API",
    version="2.0.0",
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
