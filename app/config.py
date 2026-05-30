"""
配置管理模块
"""

from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache

class Settings(BaseSettings):
    """应用配置"""
    
    # LLM 配置
    LLM_PROVIDER: str = "deepseek"
    LLM_API_KEY: str = ""
    LLM_BASE_URL: Optional[str] = None
    LLM_MODEL: str = "deepseek-chat"
    
    # Whisper 配置
    WHISPER_MODEL_SIZE: str = "base"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_COMPUTE_TYPE: str = "int8"
    
    # 视频处理
    FFMPEG_PATH: str = "/usr/bin/ffmpeg"
    TEMP_DIR: str = "/tmp/video_optimizer"
    MAX_VIDEO_SIZE_MB: int = 500
    ALLOWED_EXTENSIONS: str = "mp4,mov,avi,mkv"
    
    # 存储配置
    STORAGE_TYPE: str = "local"
    LOCAL_STORAGE_PATH: str = "./storage"
    
    # Redis 配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    
    # PostgreSQL 配置
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "videooptimizer"
    POSTGRES_USER: str = "admin"
    POSTGRES_PASSWORD: str = "password"
    
    # Web UI
    STREAMLIT_PORT: int = 8501
    STREAMLIT_THEME: str = "light"
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8080
    API_DEBUG: bool = True
    
    # 平台
    DEFAULT_PLATFORM: str = "douyin"
    ENABLE_CROSS_PLATFORM: bool = True
    
    # 批处理
    BATCH_SIZE: int = 4
    PARALLEL_WORKERS: int = 2
    MAX_BATCH_VIDEOS: int = 50
    
    # 日志
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/video_optimizer.log"
    
    # 安全
    SECRET_KEY: str = "your-secret-key-here"
    JWT_SECRET: str = "your-jwt-secret-here"
    TOKEN_EXPIRE_HOURS: int = 24
    
    # 功能开关
    ENABLE_AUDIO_TRANSCRIPTION: bool = True
    ENABLE_VISUAL_ANALYSIS: bool = True
    ENABLE_LLM_OPTIMIZATION: bool = True
    ENABLE_PLATFORM_ADAPTATION: bool = True
    ENABLE_BATCH_PROCESSING: bool = True
    ENABLE_A_B_TESTING: bool = False
    
    # 监控
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings():
    """获取配置单例"""
    return Settings()
