"""
浏览器上传管理器
根据平台名分发到对应上传器，统一调用
"""

import os
from typing import Dict, List, Optional, Any

from app.utils.logger import logger

from app.services.browser_upload.cdp_client import is_cdp_available, CDPClient
from app.services.browser_upload.base_uploader import UploadResult, BaseBrowserUploader

# 平台注册
from app.services.browser_upload.douyin_uploader import DouyinUploader
from app.services.browser_upload.xiaohongshu_uploader import XiaohongshuUploader
from app.services.browser_upload.bilibili_uploader import BilibiliUploader
from app.services.browser_upload.weixin_uploader import WeixinUploader
from app.services.browser_upload.youtube_uploader import YouTubeUploader
from app.services.browser_upload.tiktok_uploader import TiktokUploader


PLATFORM_UPLOADERS: Dict[str, type] = {
    "douyin": DouyinUploader,
    "xiaohongshu": XiaohongshuUploader,
    "bilibili": BilibiliUploader,
    "weixin": WeixinUploader,
    "youtube": YouTubeUploader,
    "tiktok": TiktokUploader,
}


class BrowserUploadManager:
    """
    浏览器上传管理器

    主要能力:
    - 多平台视频自动上传
    - CDP 浏览器连接健康检查
    - 统一结果汇总

    用法::

        mgr = BrowserUploadManager(cdp_url="http://127.0.0.1:9223")
        result = mgr.upload_to_platforms(
            video_path="/tmp/my.mp4",
            title="我的视频",
            description="简介",
            platforms=["douyin", "bilibili"],
        )
    """

    def __init__(self, cdp_url: str = "http://127.0.0.1:9223"):
        self.cdp_url = cdp_url

    # ─── 公共 API ─────────────────────────────────────────────

    def health_check(self) -> Dict[str, Any]:
        """健康检查：CDP 浏览器是否可用"""
        available = is_cdp_available(self.cdp_url)
        return {
            "cdp_available": available,
            "cdp_url": self.cdp_url,
            "supported_platforms": list(PLATFORM_UPLOADERS.keys()),
        }

    def list_platforms(self) -> List[Dict[str, str]]:
        """列出支持的平台"""
        platforms = []
        for pid, cls in PLATFORM_UPLOADERS.items():
            platforms.append(
                {
                    "platform_id": pid,
                    "display_name": cls.display_name,
                    "upload_url": cls.upload_url,
                }
            )
        return platforms

    def upload_to_platforms(
        self,
        video_path: str,
        title: str,
        platforms: List[str],
        description: str = "",
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        上传视频到多个平台。

        Args:
            video_path: 本地视频文件绝对路径
            title: 视频标题
            platforms: 目标平台列表（见 PLATFORM_UPLOADERS.keys()）
            description: 视频简介/描述
            tags: 标签列表

        Returns:
            dict - 每个平台的上传结果 + 汇总统计
        """
        # 校验文件
        if not os.path.isfile(video_path):
            return {
                "total": len(platforms),
                "success": 0,
                "failed": len(platforms),
                "results": [
                    {
                        "platform": p,
                        "success": False,
                        "message": f"视频文件不存在: {video_path}",
                    }
                    for p in platforms
                ],
            }

        # 校验平台
        valid_platforms = []
        invalid = []
        for p in platforms:
            p_lower = p.lower()
            if p_lower in PLATFORM_UPLOADERS:
                valid_platforms.append(p_lower)
            else:
                invalid.append(p)

        results: List[Dict[str, Any]] = []

        # 逐个平台上传（避免同一个浏览器窗口并发冲突）
        for p in valid_platforms:
            uploader_cls = PLATFORM_UPLOADERS[p]
            uploader: BaseBrowserUploader = uploader_cls(cdp_url=self.cdp_url)
            try:
                result: UploadResult = uploader.upload(
                    video_path=video_path,
                    title=title,
                    description=description,
                    tags=tags or [],
                )
                results.append(result.to_dict())
            except Exception as e:
                logger.exception(f"[{p}] 浏览器上传异常")
                results.append(
                    {
                        "platform": p,
                        "success": False,
                        "message": f"上传异常: {e}",
                    }
                )

        # 对无效平台返回错误信息
        for p in invalid:
            results.append(
                {
                    "platform": p,
                    "success": False,
                    "message": f"不支持的平台，可选: {list(PLATFORM_UPLOADERS.keys())}",
                }
            )

        success_count = sum(1 for r in results if r["success"])
        return {
            "total": len(results),
            "success": success_count,
            "failed": len(results) - success_count,
            "results": results,
        }

    # ─── 便捷方法 ─────────────────────────────────────────────

    def check_browser_session(self, url: str) -> Dict[str, Any]:
        """检查浏览器是否能访问某个 URL（用于确认登录状态）"""
        if not is_cdp_available(self.cdp_url):
            return {"ok": False, "message": "CDP 浏览器不可用"}

        client = CDPClient(cdp_url=self.cdp_url)
        try:
            client.connect()
            client.navigate(url, wait_seconds=3.0)
            current_url = client.get_url()
            current_title = client.get_title()
            screenshot = client.screenshot()
            client.disconnect()
            return {
                "ok": True,
                "url": current_url,
                "title": current_title,
                "screenshot": screenshot,
            }
        except Exception as e:
            client.disconnect()
            return {"ok": False, "message": str(e)}

    def get_uploader(self, platform: str) -> Optional[BaseBrowserUploader]:
        """获取特定平台的上传器实例"""
        uploader_cls = PLATFORM_UPLOADERS.get(platform.lower())
        if not uploader_cls:
            return None
        return uploader_cls(cdp_url=self.cdp_url)
