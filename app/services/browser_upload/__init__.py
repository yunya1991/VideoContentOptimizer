"""
browser_upload —— 基于 CDP 浏览器自动化的视频上传模块

依赖:
  - websocket-client (pip install websocket-client)
  - tencent-novnc-chromium-cdp Skill （部署远程浏览器环境）

支持平台:
  - douyin      抖音创作者平台
  - xiaohongshu 小红书创作服务平台
  - bilibili    哔哩哔哩创作中心
  - weixin      微信视频号助手
  - youtube     YouTube Studio
  - tiktok      TikTok Creator Center

入口:
  app.services.browser_upload.manager.BrowserUploadManager
"""

from app.services.browser_upload.manager import (
    BrowserUploadManager,
    PLATFORM_UPLOADERS,
)
from app.services.browser_upload.base_uploader import (
    BaseBrowserUploader,
    UploadResult,
)
from app.services.browser_upload.cdp_client import (
    CDPClient,
    CDPError,
    is_cdp_available,
    cdp_session,
)

__all__ = [
    "BrowserUploadManager",
    "PLATFORM_UPLOADERS",
    "BaseBrowserUploader",
    "UploadResult",
    "CDPClient",
    "CDPError",
    "is_cdp_available",
    "cdp_session",
]
