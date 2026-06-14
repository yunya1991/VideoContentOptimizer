"""
浏览器上传管理器
根据平台名分发到对应上传器，统一调用。

新增能力:
- 从 app.config 读取 CDP 配置（单一真相源）
- 每平台自动重试，默认 3 次
- 输出结构化 upload_id 和 attempts 数组，方便排障
"""

import os
import time
import uuid
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


def _read_cdp_config():
    """从 app.config 读取 CDP 默认配置（单一真相源）"""
    try:
        from app.config import get_settings
        s = get_settings()
        return {
            "cdp_url": getattr(s, "CDP_URL", "http://127.0.0.1:9223"),
            "max_retry": getattr(s, "CDP_MAX_RETRY", 3),
            "retry_delay": getattr(s, "CDP_RETRY_DELAY", 2.0),
            "upload_timeout": getattr(s, "CDP_UPLOAD_TIMEOUT", 300),
        }
    except Exception:
        return {
            "cdp_url": "http://127.0.0.1:9223",
            "max_retry": 3,
            "retry_delay": 2.0,
            "upload_timeout": 300,
        }


class BrowserUploadManager:
    """
    浏览器上传管理器

    主要能力:
    - 多平台视频自动上传（CDP 控制远程 Chromium）
    - CDP 浏览器连接健康检查
    - 统一结果汇总（含重试次数 / 截图路径）
    """

    def __init__(
        self,
        cdp_url: Optional[str] = None,
        max_retry: Optional[int] = None,
        retry_delay: Optional[float] = None,
    ):
        cfg = _read_cdp_config()
        self.cdp_url = cdp_url or cfg["cdp_url"]
        self.max_retry = max_retry if max_retry is not None else cfg["max_retry"]
        self.retry_delay = retry_delay if retry_delay is not None else cfg["retry_delay"]
        self.upload_timeout = cfg["upload_timeout"]

    # ─── 公共 API ─────────────────────────────────────────────

    def health_check(self) -> Dict[str, Any]:
        """健康检查：CDP 浏览器是否可用"""
        available = is_cdp_available(self.cdp_url)
        return {
            "cdp_available": available,
            "cdp_url": self.cdp_url,
            "max_retry": self.max_retry,
            "retry_delay": self.retry_delay,
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
        上传视频到多个平台，每平台独立重试。

        Args:
            video_path: 本地视频文件绝对路径
            title: 视频标题
            platforms: 目标平台列表（见 PLATFORM_UPLOADERS.keys()）
            description: 视频简介/描述
            tags: 标签列表

        Returns:
            dict - 结构:
              {
                "upload_id": "uuid",
                "total": 3,
                "success": 2,
                "failed": 1,
                "cdp_url": "http://127.0.0.1:9223",
                "results": [
                  {
                    "platform": "douyin",
                    "success": True,
                    "attempts": 2,
                    "message": "...",
                    "screenshot": "/tmp/cdp_xxx.png",
                    "video_path": "/tmp/xxx.mp4",
                    "upload_url": "https://creator.douyin.com/..."
                  },
                  ...
                ]
              }
        """
        upload_id = uuid.uuid4().hex[:12]
        start_time = time.time()

        # 校验文件
        if not os.path.isfile(video_path):
            return {
                "upload_id": upload_id,
                "cdp_url": self.cdp_url,
                "total": len(platforms),
                "success": 0,
                "failed": len(platforms),
                "duration_sec": 0.0,
                "results": [
                    {
                        "platform": p,
                        "success": False,
                        "attempts": 0,
                        "message": f"视频文件不存在: {video_path}",
                        "screenshot": None,
                        "video_path": video_path,
                        "upload_url": "",
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

            attempt_list = []
            last_error = None
            last_result_dict: Optional[Dict[str, Any]] = None

            for attempt in range(1, self.max_retry + 1):
                try:
                    logger.info(
                        f"[{upload_id}][{p}] 上传尝试 {attempt}/{self.max_retry}"
                    )
                    result: UploadResult = uploader.upload(
                        video_path=video_path,
                        title=title,
                        description=description,
                        tags=tags or [],
                    )
                    res_dict = result.to_dict()
                    attempt_list.append(
                        {
                            "attempt": attempt,
                            "success": res_dict.get("success", False),
                            "message": res_dict.get("message", ""),
                        }
                    )

                    if res_dict.get("success"):
                        last_result_dict = res_dict
                        logger.info(f"[{upload_id}][{p}] 上传成功（尝试 {attempt} 次）")
                        break
                    else:
                        last_error = res_dict.get("message", "uploader 判定失败")
                        logger.warning(
                            f"[{upload_id}][{p}] 上传未成功（尝试 {attempt} 次）: {last_error}"
                        )

                except Exception as e:
                    last_error = str(e)
                    attempt_list.append(
                        {"attempt": attempt, "success": False, "message": last_error}
                    )
                    logger.exception(f"[{upload_id}][{p}] 上传异常（尝试 {attempt} 次）")

                # 下一次重试前等待
                if attempt < self.max_retry:
                    time.sleep(self.retry_delay)
            else:
                logger.warning(
                    f"[{upload_id}][{p}] 已用尽 {self.max_retry} 次上传，放弃"
                )

            # 汇总该平台结果
            success = last_result_dict is not None and last_result_dict.get("success", False)
            base = {
                "platform": p,
                "success": success,
                "attempts": len(attempt_list),
                "message": (last_result_dict.get("message") if success else last_error) or "",
                "screenshot": last_result_dict.get("screenshot") if last_result_dict else None,
                "video_path": video_path,
                "upload_url": last_result_dict.get("upload_url", "") if last_result_dict else "",
            }
            results.append(base)

        # 对无效平台返回错误信息
        for p in invalid:
            results.append(
                {
                    "platform": p,
                    "success": False,
                    "attempts": 0,
                    "message": f"不支持的平台，可选: {list(PLATFORM_UPLOADERS.keys())}",
                    "screenshot": None,
                    "video_path": video_path,
                    "upload_url": "",
                }
            )

        success_count = sum(1 for r in results if r["success"])
        return {
            "upload_id": upload_id,
            "cdp_url": self.cdp_url,
            "total": len(results),
            "success": success_count,
            "failed": len(results) - success_count,
            "duration_sec": round(time.time() - start_time, 2),
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
            try:
                client.disconnect()
            except Exception:
                pass
            return {"ok": False, "message": str(e)}

    def get_uploader(self, platform: str) -> Optional[BaseBrowserUploader]:
        """获取特定平台的上传器实例"""
        uploader_cls = PLATFORM_UPLOADERS.get(platform.lower())
        if not uploader_cls:
            return None
        return uploader_cls(cdp_url=self.cdp_url)
