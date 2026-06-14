"""
浏览器上传器基类
所有平台上传器继承此基类，统一接口
"""

import time
import os
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod

from app.utils.logger import logger
from app.services.browser_upload.cdp_client import CDPClient, CDPError, is_cdp_available


class UploadResult:
    """上传结果"""

    def __init__(
        self,
        platform: str,
        success: bool,
        message: str = "",
        screenshot: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.platform = platform
        self.success = success
        self.message = message
        self.screenshot = screenshot
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform,
            "success": self.success,
            "message": self.message,
            "screenshot": self.screenshot,
            "details": self.details,
        }


class BaseBrowserUploader(ABC):
    """
    浏览器自动化上传器基类

    子类需实现：
    - upload_url: 平台上传页面 URL
    - _do_upload: 执行实际的上传操作流程
    - display_name: 平台显示名
    """

    upload_url: str = ""
    display_name: str = ""
    platform_id: str = ""

    # 视频标题 CSS 选择器
    title_selector: str = ""
    # 视频描述 CSS 选择器
    description_selector: str = ""
    # 文件上传 input[type=file] 选择器
    file_input_selector: str = ""
    # 提交按钮文本（用于匹配）
    submit_button_text: str = ""
    # 提交按钮 CSS 选择器（优先使用）
    submit_button_selector: str = ""

    def __init__(
        self,
        cdp_url: str = "http://127.0.0.1:9223",
        require_login: bool = True,
        max_wait_upload: int = 120,
    ):
        self.cdp_url = cdp_url
        self.require_login = require_login
        self.max_wait_upload = max_wait_upload

    # ─── 公开接口 ─────────────────────────────────────────────────

    def upload(
        self,
        video_path: str,
        title: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        **kwargs,
    ) -> UploadResult:
        """
        执行完整的上传流程。

        Args:
            video_path: 本地视频文件绝对路径
            title: 视频标题
            description: 视频描述
            tags: 标签列表
            **kwargs: 平台特定参数

        Returns:
            UploadResult
        """
        if not os.path.isfile(video_path):
            return UploadResult(
                platform=self.platform_id,
                success=False,
                message=f"视频文件不存在: {video_path}",
            )

        if not is_cdp_available(self.cdp_url):
            return UploadResult(
                platform=self.platform_id,
                success=False,
                message="CDP 浏览器不可用（需要先部署 tencent-novnc-chromium-cdp Skill）",
            )

        client: Optional[CDPClient] = None
        screenshot_path: Optional[str] = None

        try:
            logger.info(f"[{self.display_name}] 开始上传: {os.path.basename(video_path)}")
            client = CDPClient(cdp_url=self.cdp_url)
            client.connect()

            # 1) 导航到上传页面
            logger.info(f"[{self.display_name}] 访问: {self.upload_url}")
            client.navigate(self.upload_url, wait_seconds=5.0)

            # 2) 登录检查
            if self.require_login and self._needs_login(client):
                logger.warning(f"[{self.display_name}] 检测到需要登录")
                login_hint = self._get_login_hint()
                # 截图留证
                try:
                    screenshot_path = client.screenshot()
                except Exception:
                    pass
                return UploadResult(
                    platform=self.platform_id,
                    success=False,
                    message=f"需要登录。{login_hint}",
                    screenshot=screenshot_path,
                    details={"needs_login": True},
                )

            # 3) 执行平台特定的上传流程
            result = self._do_upload(
                client=client,
                video_path=video_path,
                title=title,
                description=description,
                tags=tags or [],
                **kwargs,
            )

            # 4) 最终截图确认
            try:
                result.screenshot = client.screenshot()
            except Exception as e:
                logger.warning(f"[{self.display_name}] 截图失败: {e}")

            logger.info(
                f"[{self.display_name}] 上传{'成功' if result.success else '失败'}: {result.message}"
            )
            return result

        except CDPError as e:
            return UploadResult(
                platform=self.platform_id,
                success=False,
                message=f"CDP 错误: {e}",
                screenshot=screenshot_path,
            )
        except Exception as e:
            logger.exception(f"[{self.display_name}] 上传异常")
            return UploadResult(
                platform=self.platform_id,
                success=False,
                message=f"上传异常: {e}",
                screenshot=screenshot_path,
            )
        finally:
            if client:
                client.disconnect()

    # ─── 子类需实现 ───────────────────────────────────────────────

    @abstractmethod
    def _do_upload(
        self,
        client: "CDPClient",
        video_path: str,
        title: str,
        description: str,
        tags: List[str],
        **kwargs,
    ) -> UploadResult:
        """
        执行平台特定的上传流程。

        在调用此方法前：
        - 已连接 CDP 浏览器
        - 已导航到 upload_url
        - 已通过登录检查

        子类实现：
        1. 上传视频文件（client.upload_file）
        2. 等待视频处理（轮询）
        3. 填写标题、描述（client.fill_text / client.set_textarea_content）
        4. 设置标签（如有）
        5. 点击提交按钮（client.click / client.select_by_contains_text）
        """
        raise NotImplementedError

    # ─── 可覆盖方法 ───────────────────────────────────────────────

    def _needs_login(self, client: "CDPClient") -> bool:
        """
        检查页面是否需要登录。
        默认逻辑：当前 URL 是否包含 login 或当前标题是否包含登录/登录
        可由子类覆盖以实现更精确的检测
        """
        url = client.get_url().lower()
        title = client.get_title().lower()

        login_keywords = [
            "login", "signin", "sign-in", "sign in",
            "登录", "登陆", "登入", "未登录",
            "auth", "oauth", "account",
        ]
        for kw in login_keywords:
            if kw in url or kw in title:
                return True
        return False

    def _get_login_hint(self) -> str:
        """获取登录提示信息"""
        return "请在 noVNC 浏览器中手动完成登录，然后重新调用上传接口。"

    # ─── 通用辅助方法（给子类复用） ─────────────────────────────

    def _fill_title(self, client: "CDPClient", title: str) -> bool:
        """填写标题（通用实现）"""
        if not self.title_selector:
            return False
        try:
            return client.fill_text(self.title_selector, title, wait_after=0.5)
        except Exception as e:
            logger.warning(f"[{self.platform_id}] 填写标题失败: {e}")
            return False

    def _fill_description(self, client: "CDPClient", description: str) -> bool:
        """填写描述（通用实现）"""
        if not self.description_selector or not description:
            return True
        try:
            return client.set_textarea_content(
                self.description_selector, description, wait_after=0.5
            )
        except Exception as e:
            logger.warning(f"[{self.platform_id}] 填写描述失败: {e}")
            return False

    def _click_submit(self, client: "CDPClient", wait_after: float = 3.0) -> bool:
        """点击提交按钮"""
        try:
            if self.submit_button_selector:
                ok = client.click(self.submit_button_selector, wait_after=wait_after)
                if ok:
                    return True

            if self.submit_button_text:
                ok = client.select_by_contains_text(
                    "button", self.submit_button_text, wait_after=wait_after
                )
                if ok:
                    return True
                # 再试一次 span
                ok = client.select_by_contains_text(
                    "span", self.submit_button_text, wait_after=wait_after
                )
                if ok:
                    return True

            return False
        except Exception as e:
            logger.warning(f"[{self.platform_id}] 点击提交按钮失败: {e}")
            return False

    def _wait_for_upload_progress(
        self,
        client: "CDPClient",
        progress_selector: Optional[str] = None,
        max_wait: Optional[int] = None,
    ) -> bool:
        """
        等待视频上传处理完成。

        默认策略：简单等待 + 轮询特定元素；子类可覆盖实现更精确的进度检测
        """
        max_wait = max_wait or self.max_wait_upload
        deadline = time.time() + max_wait

        # 先等待文件上传开始
        time.sleep(5)

        # 如果没有特定进度选择器，用简单的"等待一段较长时间"策略
        if not progress_selector:
            # 通用策略：每 5 秒检查一次页面状态，总时长不超过 max_wait
            slept = 0
            interval = 5
            while slept < max_wait:
                time.sleep(interval)
                slept += interval
                # 检查是否还有上传进度指示
                try:
                    res = client.execute_js(
                        "document.body.innerText.includes('上传') || "
                        "document.body.innerText.includes('处理') || "
                        "document.body.innerText.includes('转码') || "
                        "document.body.innerText.includes('waiting')",
                        return_by_value=True,
                    )
                    still_uploading = res.get("result", {}).get("value", False)
                    if not still_uploading:
                        return True
                except Exception:
                    pass
            return True

        # 有进度选择器：等待该元素消失或达到 100%
        while time.time() < deadline:
            try:
                res = client.execute_js(
                    f"""(() => {{
                        const el = document.querySelector({repr(progress_selector)});
                        if (!el) return {{ done:true }};
                        const text = el.textContent || '';
                        return {{ text:text, exists:true }};
                    }})()""",
                    return_by_value=True,
                )
                val = res.get("result", {}).get("value", {})
                if val.get("done"):
                    return True
                if isinstance(val, dict) and "100%" in str(val.get("text", "")):
                    return True
            except Exception:
                pass
            time.sleep(3)

        # 超时但继续（可能只是进度检测不精确）
        logger.warning(f"[{self.platform_id}] 上传进度等待超时，继续后续流程")
        return True
