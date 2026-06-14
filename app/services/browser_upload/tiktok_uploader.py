"""
TikTok Creator Center 上传器
URL: https://www.tiktok.com/tiktokstudio/upload
"""

import time
from typing import List

from app.utils.logger import logger
from app.services.browser_upload.base_uploader import BaseBrowserUploader, UploadResult
from app.services.browser_upload.cdp_client import CDPClient


class TiktokUploader(BaseBrowserUploader):
    """TikTok 视频上传（浏览器自动化）"""

    upload_url = "https://www.tiktok.com/tiktokstudio/upload"
    display_name = "TikTok Creator Center"
    platform_id = "tiktok"

    file_input_selector = 'input[type="file"]'
    submit_button_text = "Post"

    def _needs_login(self, client: "CDPClient") -> bool:
        url = client.get_url().lower()
        title = client.get_title().lower()

        if "login" in url or "signin" in url or "auth" in url:
            return True
        if "login" in title or "sign in" in title:
            return True

        if "tiktok.com" not in url:
            return True

        return False

    def _get_login_hint(self) -> str:
        return (
            "TikTok 需要登录。请在 noVNC 浏览器中完成账号登录（推荐扫码登录），"
            "登录状态会保存在浏览器中。"
        )

    def _do_upload(
        self,
        client: "CDPClient",
        video_path: str,
        title: str,
        description: str,
        tags: List[str],
        **kwargs,
    ) -> UploadResult:
        """TikTok 上传流程"""

        # 1) 上传视频
        logger.info(f"[{self.platform_id}] 上传视频")
        client.wait_for_element('input[type="file"]', max_wait=20)
        uploaded = client.upload_file(
            self.file_input_selector, video_path, wait_after=3.0
        )
        if not uploaded:
            time.sleep(3)
            uploaded = client.upload_file(
                self.file_input_selector, video_path, wait_after=5.0
            )
            if not uploaded:
                return UploadResult(
                    platform=self.platform_id,
                    success=False,
                    message="视频文件上传失败",
                )

        # 2) 等待处理
        logger.info(f"[{self.platform_id}] 等待视频处理")
        self._wait_for_upload_progress(client, max_wait=self.max_wait_upload)

        # 3) 填写标题和描述
        logger.info(f"[{self.platform_id}] 填写标题")
        full_text = title
        if description:
            full_text = f"{title}\n\n{description}"
        if tags:
            full_text += "\n\n" + " ".join(f"#{t}" for t in tags if t)

        caption_filled = False
        for sel in [
            'textarea',
            'div[contenteditable="true"]',
            'input[type="text"]',
        ]:
            try:
                ok = client.set_textarea_content(sel, full_text, wait_after=0.5)
                if ok:
                    caption_filled = True
                    break
            except Exception:
                continue

        if not caption_filled:
            try:
                client.execute_js(
                    f"""(() => {{
                        const inputs = document.querySelectorAll('textarea, div[contenteditable="true"]');
                        for (let el of inputs) {{
                            if (el.offsetParent !== null) {{
                                el.focus();
                                if (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT') {{
                                    el.value = {repr(full_text)};
                                }} else {{
                                    el.innerHTML = {repr(full_text)};
                                }}
                                el.dispatchEvent(new Event('input', {{ bubbles:true }}));
                                return {{ ok:true }};
                            }}
                        }}
                        return {{ ok:false }};
                    }})()""",
                    return_by_value=True,
                )
                caption_filled = True
            except Exception:
                pass

        # 4) 提交（Post / Publish）
        logger.info(f"[{self.platform_id}] 提交发布")
        submitted = False
        for btn_text in ["Post", "发布", "PUBLISH", "post", "POST"]:
            for tag in ["button", "span", "div"]:
                if client.select_by_contains_text(tag, btn_text, wait_after=2.0):
                    submitted = True
                    break
            if submitted:
                break

        client.wait(3.0)

        return UploadResult(
            platform=self.platform_id,
            success=True,
            message="TikTok 发布流程已执行（请在 TikTok Studio 确认状态）",
            details={
                "caption_set": caption_filled,
                "tags_set": len(tags) > 0,
                "submitted": submitted,
                "current_url": client.get_url(),
            },
        )
