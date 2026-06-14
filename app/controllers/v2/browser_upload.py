"""
API v2 - 浏览器自动化上传控制器

提供接口:
  POST   /api/v2/browser-upload/upload          上传视频到指定平台
  POST   /api/v2/browser-upload/upload-file     直接从 multipart 上传视频文件
  GET    /api/v2/browser-upload/platforms       列出支持的平台
  GET    /api/v2/browser-upload/health          CDP 浏览器健康检查
  POST   /api/v2/browser-upload/session-check   检查浏览器访问状态
"""

import os
import uuid
import tempfile
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Query
from pydantic import BaseModel

from app.utils.logger import logger
from app.services.browser_upload.manager import BrowserUploadManager
from app.config import get_settings

router = APIRouter(prefix="/browser-upload", tags=["浏览器上传"])

settings = get_settings()


# ─── 请求/响应模型 ─────────────────────────────────────────────

class UploadRequest(BaseModel):
    """基于本地文件路径的上传请求"""
    video_path: str
    title: str
    platforms: List[str]
    description: str = ""
    tags: Optional[List[str]] = None
    cdp_url: Optional[str] = None


class UploadResponse(BaseModel):
    """上传响应"""
    total: int
    success: int
    failed: int
    results: List[dict]


class PlatformInfo(BaseModel):
    platform_id: str
    display_name: str
    upload_url: str


class SessionCheckRequest(BaseModel):
    url: str
    cdp_url: Optional[str] = None


class SessionCheckResponse(BaseModel):
    ok: bool
    url: Optional[str] = None
    title: Optional[str] = None
    screenshot: Optional[str] = None
    message: Optional[str] = None


# ─── 内部工具 ─────────────────────────────────────────────────

def _get_cdp_url(override: Optional[str] = None) -> str:
    """获取 CDP URL：优先使用请求参数，其次使用配置"""
    if override:
        return override
    # 从配置获取（若配置中未定义则用默认）
    return getattr(settings, "CDP_URL", "http://127.0.0.1:9223")


def _save_uploaded_file(file: UploadFile) -> str:
    """保存上传的视频文件到临时目录，返回路径"""
    safe_name = os.path.basename(file.filename or f"video_{uuid.uuid4().hex}.mp4")
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    temp_dir = settings.TEMP_DIR if hasattr(settings, "TEMP_DIR") else tempfile.gettempdir()
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, unique_name)

    total_size = 0
    max_bytes = (
        (settings.MAX_VIDEO_SIZE_MB if hasattr(settings, "MAX_VIDEO_SIZE_MB") else 500)
        * 1024
        * 1024
    )

    with open(temp_path, "wb") as buffer:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > max_bytes:
                buffer.close()
                os.remove(temp_path)
                raise HTTPException(
                    status_code=413,
                    detail=f"文件过大，最大允许 {max_bytes // 1024 // 1024} MB",
                )
            buffer.write(chunk)

    logger.info(f"浏览器上传 - 保存视频到: {temp_path} ({total_size} bytes)")
    return temp_path


# ─── API 路由 ───────────────────────────────────────────────────

@router.get("/platforms", response_model=List[PlatformInfo], summary="列出支持的平台")
async def list_platforms():
    """获取支持的视频上传平台列表"""
    manager = BrowserUploadManager()
    return manager.list_platforms()


@router.get("/health", summary="CDP 浏览器健康检查")
async def health_check(cdp_url: Optional[str] = Query(None, description="CDP 地址，默认 http://127.0.0.1:9223")):
    """检查 CDP 浏览器是否可用"""
    cdp = _get_cdp_url(cdp_url)
    manager = BrowserUploadManager(cdp_url=cdp)
    return manager.health_check()


@router.post("/upload", response_model=UploadResponse, summary="上传本地视频到多平台")
async def upload_from_path(req: UploadRequest):
    """
    从服务器本地路径上传视频到一个或多个平台。

    **注意**：video_path 必须是服务器可访问的绝对路径。
    """
    if not os.path.isfile(req.video_path):
        raise HTTPException(status_code=400, detail=f"视频文件不存在: {req.video_path}")

    cdp = _get_cdp_url(req.cdp_url)
    manager = BrowserUploadManager(cdp_url=cdp)

    result = manager.upload_to_platforms(
        video_path=req.video_path,
        title=req.title,
        platforms=req.platforms,
        description=req.description,
        tags=req.tags,
    )
    return result


@router.post("/upload-file", response_model=UploadResponse, summary="上传视频文件到多平台")
async def upload_from_file(
    video: UploadFile = File(..., description="视频文件（mp4/mov/avi/mkv）"),
    title: str = Form(..., description="视频标题"),
    platforms: str = Form(..., description="目标平台，逗号分隔，如: douyin,bilibili"),
    description: str = Form("", description="视频简介"),
    tags: Optional[str] = Form(None, description="标签，逗号分隔"),
    cdp_url: Optional[str] = Form(None, description="CDP 地址"),
):
    """
    通过文件上传视频到一个或多个平台。

    **典型流程**：
    1. 上传视频文件
    2. 系统保存到临时目录
    3. 通过 CDP 浏览器分别在各平台完成上传
    4. 返回每个平台的执行状态及截图路径

    **平台列表**：douyin, xiaohongshu, bilibili, weixin, youtube, tiktok
    """
    # 解析 platforms
    platform_list = [p.strip() for p in platforms.split(",") if p.strip()]
    if not platform_list:
        raise HTTPException(status_code=400, detail="必须指定至少一个平台")

    # 解析 tags
    tag_list = [t.strip() for t in (tags or "").split(",") if t.strip()]

    # 保存文件
    temp_path = _save_uploaded_file(video)

    cdp = _get_cdp_url(cdp_url)
    manager = BrowserUploadManager(cdp_url=cdp)

    try:
        result = manager.upload_to_platforms(
            video_path=temp_path,
            title=title,
            platforms=platform_list,
            description=description,
            tags=tag_list,
        )
        return result
    finally:
        # 清理临时文件（上传完成后删除）
        try:
            if os.path.isfile(temp_path):
                os.remove(temp_path)
        except OSError as e:
            logger.warning(f"清理临时文件失败 {temp_path}: {e}")


@router.post("/session-check", response_model=SessionCheckResponse, summary="检查浏览器会话")
async def check_session(req: SessionCheckRequest):
    """
    检查远程浏览器是否能访问某个 URL，返回 URL、标题和截图。
    常用于确认平台登录状态。
    """
    cdp = _get_cdp_url(req.cdp_url)
    manager = BrowserUploadManager(cdp_url=cdp)
    return manager.check_browser_session(req.url)
