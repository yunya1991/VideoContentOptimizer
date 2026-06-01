"""
upload-post.com 视频发布客户端
移植自 MoneyPrinterTurbo app/services/upload_post.py

支持平台（upload-post.com platform 标识）:
  tiktok, youtube, instagram, facebook, twitter, linkedin, pinterest, snapchat

本项目平台名映射:
  douyin      → tiktok  (抖音即 TikTok 国内版)
  xiaohongshu → 不支持，跳过并日志提示
  weixin      → 不支持，跳过并日志提示
  其余名称若已是 upload-post.com 标识则直传
"""

import os
from typing import Dict, List, Optional, Tuple

import requests

from app.utils.logger import logger

# 平台名映射：本项目 → upload-post.com 标识
_PLATFORM_MAP: Dict[str, str] = {
    "douyin":    "tiktok",
    "tiktok":    "tiktok",
    "youtube":   "youtube",
    "instagram": "instagram",
    "facebook":  "facebook",
    "twitter":   "twitter",
    "linkedin":  "linkedin",
    "pinterest": "pinterest",
    "snapchat":  "snapchat",
}

# upload-post.com 目前不支持这些平台
_UNSUPPORTED_PLATFORMS = {"xiaohongshu", "weixin", "wechat", "bilibili"}


class UploadPostClient:
    """
    upload-post.com REST API 客户端。

    用法::

        client = UploadPostClient(api_key="...", username="...")
        result = client.upload(
            video_path="/tmp/video.mp4",
            title="我的视频",
            platforms=["douyin", "youtube"],
        )
    """

    BASE_URL = "https://api.upload-post.com"

    def __init__(
        self,
        api_key: str,
        username: str = "",
        base_url: str = BASE_URL,
    ):
        if not api_key:
            raise ValueError("UPLOAD_POST_API_KEY 未配置，无法发布视频")
        self.api_key = api_key
        self.username = username
        self.base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Apikey {api_key}"}

    # ─── 公开接口 ──────────────────────────────────────────────────────────

    def upload(
        self,
        video_path: str,
        title: str,
        platforms: List[str],
        privacy_level: str = "public",
    ) -> Dict:
        """
        上传视频到指定平台列表。

        参数:
          video_path    - 本地视频文件路径
          title         - 视频标题（自动截断至 2200 字符）
          platforms     - 目标平台列表（支持本项目平台名或 upload-post.com 标识）
          privacy_level - 隐私级别: public / friends / private

        返回::

          {
            "request_id": str,
            "platforms":  [str],   # 实际提交的平台
            "skipped":    [str],   # 跳过的不支持平台
            "response":   dict,    # API 原始响应
          }

        异常:
          FileNotFoundError  - 视频文件不存在
          ValueError         - api_key 未配置或无有效平台
          RuntimeError       - API 返回 4xx/5xx
        """
        if not os.path.isfile(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        mapped, skipped = self._map_platforms(platforms)
        if not mapped:
            raise ValueError(
                f"所有平台均不受支持，跳过发布。不支持的平台: {platforms}"
            )

        data: Dict = {
            "user": self.username,
            "title": title[:2200],
            "privacy_level": privacy_level,
        }
        for i, platform in enumerate(mapped):
            data[f"platform[{i}]"] = platform

        logger.info(f"[upload-post] 开始上传到 {mapped}，文件: {video_path}")
        with open(video_path, "rb") as video_file:
            response = requests.post(
                f"{self.base_url}/api/upload_video",
                headers=self._headers,
                data=data,
                files={"video": video_file},
                timeout=300,
            )

        if response.status_code >= 400:
            raise RuntimeError(
                f"upload-post.com 返回错误 {response.status_code}: {response.text[:500]}"
            )

        try:
            body = response.json()
        except Exception:
            body = {"raw": response.text}

        request_id = body.get("request_id") or body.get("id") or ""
        logger.info(f"[upload-post] 上传成功，request_id={request_id}")

        return {
            "request_id": request_id,
            "platforms": mapped,
            "skipped": skipped,
            "response": body,
        }

    def check_status(self, request_id: str) -> Optional[Dict]:
        """
        查询发布任务状态。

        返回 API 响应 dict；404 时返回 None；其他错误抛 RuntimeError。
        """
        response = requests.get(
            f"{self.base_url}/api/status/{request_id}",
            headers=self._headers,
            timeout=30,
        )
        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise RuntimeError(
                f"状态查询失败 {response.status_code}: {response.text[:200]}"
            )
        return response.json()

    # ─── 私有方法 ──────────────────────────────────────────────────────────

    def _map_platforms(self, platforms: List[str]) -> Tuple[List[str], List[str]]:
        """将平台名映射为 upload-post.com 标识，去重，跳过不支持的平台。"""
        mapped: List[str] = []
        skipped: List[str] = []
        seen: set = set()

        for p in platforms:
            p_lower = p.lower()
            if p_lower in _UNSUPPORTED_PLATFORMS:
                logger.warning(
                    f"[upload-post] {p} 暂不支持（upload-post.com 无此平台），已跳过"
                )
                skipped.append(p)
            else:
                target = _PLATFORM_MAP.get(p_lower, p_lower)
                if target not in seen:
                    mapped.append(target)
                    seen.add(target)

        return mapped, skipped


class PublishManager:
    """
    视频发布管理器，封装 UploadPostClient，处理配置读取和多平台协调。

    未启用（UPLOAD_POST_ENABLED=false）时所有方法均静默返回，不抛异常。
    """

    def __init__(
        self,
        api_key: str = "",
        username: str = "",
        enabled: bool = False,
        default_platforms: Optional[List[str]] = None,
    ):
        self.enabled = enabled
        self.default_platforms: List[str] = default_platforms or ["tiktok"]
        self._client: Optional[UploadPostClient] = None
        if enabled and api_key:
            self._client = UploadPostClient(api_key=api_key, username=username)

    @classmethod
    def from_settings(cls) -> "PublishManager":
        from app.config import get_settings
        s = get_settings()
        return cls(
            api_key=getattr(s, "UPLOAD_POST_API_KEY", ""),
            username=getattr(s, "UPLOAD_POST_USERNAME", ""),
            enabled=getattr(s, "UPLOAD_POST_ENABLED", False),
            default_platforms=getattr(s, "UPLOAD_POST_PLATFORMS", ["tiktok"]),
        )

    def publish(
        self,
        video_path: str,
        title: str,
        platforms: Optional[List[str]] = None,
    ) -> Dict:
        """
        发布视频到多个平台。

        未启用时返回空 dict，无异常。

        异常:
          ValueError         - 已启用但 api_key 未配置
          FileNotFoundError  - 视频文件不存在
          RuntimeError       - 上传 API 返回错误
        """
        if not self.enabled:
            logger.info("[PublishManager] 发布功能未启用（UPLOAD_POST_ENABLED=false）")
            return {}

        if not self._client:
            raise ValueError("UPLOAD_POST_API_KEY 未配置，无法发布")

        if not os.path.isfile(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        target_platforms = platforms or self.default_platforms
        return self._client.upload(
            video_path=video_path,
            title=title,
            platforms=target_platforms,
        )
