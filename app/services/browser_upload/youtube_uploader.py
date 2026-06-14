"""
YouTube Studio 上传器（备选方案，upload-post.com 失败时使用）
URL: https://studio.youtube.com/create/video
"""

import time
from typing import List

from app.utils.logger import logger
from app.services.browser_upload.base_uploader import BaseBrowserUploader, UploadResult
from app.services.browser_upload.cdp_client import CDPClient


class YouTubeUploader(BaseBrowserUploader):
    """YouTube 视频上传（浏览器自动化）"""

    upload_url = "https://studio.youtube.com/create/video"
    display_name = "YouTube Studio"
    platform_id = "youtube"

    file_input_selector = 'input[type="file"]'
    submit_button_text = "Publish"

    def _needs_login(self, client: "CDPClient") -> bool:
        url = client.get_url().lower()
        title = client.get_title().lower()

        if "accounts.google.com" in url or "signin" in url or "login" in url:
            return True
        if "sign in" in title or "login" in title:
            return True

        # 若 URL 不在 studio 或 create 路径，可能需要先进入
        if "studio.youtube.com" not in url:
            return True

        return False

    def _get_login_hint(self) -> str:
        return (
            "YouTube 需使用 Google 账号登录。请在 noVNC 浏览器中完成登录，"
            "建议登录后保持浏览器会话以便下次直接发布。"
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
        """YouTube 上传流程"""

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

        # 3) 填写标题
        logger.info(f"[{self.platform_id}] 填写标题")
        title_filled = False
        for sel in [
            'input[id*="title"]',
            "textarea",
            "input[type='text']",
        ]:
            try:
                ok = client.fill_text(sel, title, wait_after=0.5)
                if ok:
                    title_filled = True
                    break
            except Exception:
                continue

        if not title_filled:
            try:
                client.execute_js(
                    f"""(() => {{
                        const inputs = document.querySelectorAll('input[type="text"], textarea');
                        for (let el of inputs) {{
                            if (el.offsetParent !== null) {{
                                el.focus();
                                el.value = {repr(title)};
                                el.dispatchEvent(new Event('input', {{ bubbles:true }}));
                                return {{ ok:true }};
                            }}
                        }}
                        return {{ ok:false }};
                    }})()""",
                    return_by_value=True,
                )
                title_filled = True
            except Exception:
                pass

        # 4) 填写描述
        if description:
            logger.info(f"[{self.platform_id}] 填写描述")
            try:
                client.execute_js(
                    f"""(() => {{
                        const editables = document.querySelectorAll('textarea, div[contenteditable="true"]');
                        let found = 0;
                        for (let el of editables) {{
                            if (el.offsetParent !== null) {{
                                found++;
                                if (found === 2) {{
                                    el.focus();
                                    if (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT') {{
                                        el.value = {repr(description)};
                                    }} else {{
                                        el.innerHTML = {repr(description)};
                                    }}
                                    el.dispatchEvent(new Event('input', {{ bubbles:true }}));
                                    return {{ ok:true }};
                                }}
                            }}
                        }}
                        return {{ ok:false, found: found }};
                    }})()""",
                    return_by_value=True,
                )
            except Exception as e:
                logger.warning(f"[{self.platform_id}] 填写描述失败: {e}")

        # 5) 添加标签（YouTube tags）
        if tags:
            logger.info(f"[{self.platform_id}] 添加标签: {tags}")
            try:
                client.execute_js(
                    f"""(() => {{
                        const editables = document.querySelectorAll('textarea, div[contenteditable="true"]');
                        for (let i = editables.length - 1; i >= 0; i--) {{
                            const el = editables[i];
                            if (el.offsetParent !== null) {{
                                const cur = el.tagName === 'TEXTAREA' || el.tagName === 'INPUT' ? el.value : el.innerHTML;
                                const extra = '\\n\\n' + {repr(', '.join(t for t in tags if t))};
                                if (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT') {{
                                    el.value = cur + extra;
                                }} else {{
                                    el.innerHTML = cur + extra;
                                }}
                                el.dispatchEvent(new Event('input', {{ bubbles:true }}));
                                return {{ ok:true }};
                            }}
                        }}
                    }})()""",
                    return_by_value=True,
                )
            except Exception:
                pass

        # 6) 点击 Next / Publish（YouTube 流程：details → video elements → visibility → publish）
        logger.info(f"[{self.platform_id}] 导航到发布")
        for step_text in ["Next", "下一步", "NEXT", "next"]:
            for tag in ["button", "span", "div"]:
                try:
                    client.select_by_contains_text(tag, step_text, wait_after=2.0)
                except Exception:
                    pass

        # 尝试点击 Publish
        submitted = False
        for btn_text in ["Publish", "发布", "publish", "PUBLISH"]:
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
            message="YouTube 发布流程已执行（请在 YouTube Studio 确认状态）",
            details={
                "title_set": title_filled,
                "description_set": bool(description),
                "tags_set": len(tags) > 0,
                "submitted": submitted,
                "current_url": client.get_url(),
            },
        )
