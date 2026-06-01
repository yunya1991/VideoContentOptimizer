"""
配置管理模块
"""

import warnings
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional, List
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
    ALLOWED_EXTENSIONS: List[str] = ["mp4", "mov", "avi", "mkv"]

    @field_validator("ALLOWED_EXTENSIONS", mode="before")
    @classmethod
    def parse_extensions(cls, v):
        if isinstance(v, str):
            return [ext.strip().lower() for ext in v.split(",") if ext.strip()]
        return v

    # TTS 配置
    # voice_name 格式：engine:voice，例如 edge:zh-CN-XiaoxiaoNeural
    # 支持引擎：edge（免费默认）/ azure / siliconflow / gemini / mimo
    TTS_VOICE_NAME: str = "edge:zh-CN-XiaoxiaoNeural"
    TTS_VOICE_RATE: int = 0        # 语速百分比，0=原速，正数加速，负数减速
    TTS_VOICE_VOLUME: float = 1.0  # 音量倍数（1.0=原始）

    # Azure Speech SDK（付费，高质量）
    AZURE_SPEECH_KEY: str = ""
    AZURE_SPEECH_REGION: str = "eastus"

    # SiliconFlow CosyVoice2（国内，有免费额度）
    SILICONFLOW_API_KEY: str = ""

    # Gemini TTS
    GEMINI_API_KEY: str = ""

    # MiMo TTS（小米）
    MIMO_API_KEY: str = ""

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
    POSTGRES_PASSWORD: str = ""

    # Web UI
    STREAMLIT_PORT: int = 8501
    STREAMLIT_THEME: str = "light"

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8080
    API_DEBUG: bool = False

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

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

    # 项目根目录（进化引擎数据存储位置）
    PROJECT_ROOT: str = "."

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
    settings = Settings()

    # 启动时安全检查
    if settings.SECRET_KEY in ("your-secret-key-here", ""):
        warnings.warn(
            "SECRET_KEY 使用默认值！生产环境请务必在 .env 中设置安全的密钥。",
            RuntimeWarning,
            stacklevel=2,
        )
    if settings.JWT_SECRET in ("your-jwt-secret-here", ""):
        warnings.warn(
            "JWT_SECRET 使用默认值！生产环境请务必在 .env 中设置安全的密钥。",
            RuntimeWarning,
            stacklevel=2,
        )

    return settings
