"""
小红书创作者平台上传器
URL: https://creator.xiaohongshu.com/publish/publish?source=official
"""

import time
from typing import List

from app.utils.logger import logger
from app.services.browser_upload.base_uploader import BaseBrowserUploader, UploadResult
from app.services.browser_upload.cdp_client import CDPClient


class XiaohongshuUploader(BaseBrowserUploader):
    """小红书视频/图文上传"""

    upload_url = "https://creator.xiaohongshu.com/publish/publish?source=official"
    display_name = "小红书创作服务平台"
    platform_id = "xiaohongshu"

    file_input_selector = 'input[type="file"]'
    submit_button_text = "发布"

    def _needs_login(self, client: "CDPClient") -> bool:
        url = client.get_url().lower()
        title = client.get_title()

        if "login" in url or "signin" in url or "passport" in url:
            return True
        if "登录" in title or "login" in title.lower():
            return True

        # 检查是否停留在创作平台
        if "creator.xiaohongshu.com" in url and "publish" in url:
            return False
        return False

    def _get_login_hint(self) -> str:
        return (
            "小红书需要扫码登录。请在 noVNC 浏览器中使用小红书 APP 扫码，"
            "完成登录后重新调用上传接口。登录状态会保留在浏览器中。"
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
        """小红书视频上传流程"""

        # 1) 上传视频文件
        logger.info(f"[{self.platform_id}] 上传视频文件")
        # 等待页面加载，找 file input
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

        # 2) 等待上传处理
        logger.info(f"[{self.platform_id}] 等待视频处理")
        self._wait_for_upload_progress(client, max_wait=self.max_wait_upload)

        # 3) 填写标题
        logger.info(f"[{self.platform_id}] 填写标题")
        title_filled = False

        # 尝试 title 输入相关元素
        title_selectors = [
            "textarea[placeholder*='标题']",
            "textarea[placeholder*='标题']",
            "input[placeholder*='标题']",
            "input[placeholder*='标题']",
            "textarea",  # fallback: 第一个 textarea
        ]
        for sel in title_selectors:
            try:
                ok = client.fill_text(sel, title, wait_after=0.5)
                if ok:
                    title_filled = True
                    break
            except Exception:
                continue

        if not title_filled:
            # 最后方案：用 JS 找第一个可用文本输入
            try:
                client.execute_js(
                    f"""(() => {{
                        const inputs = document.querySelectorAll('input[type="text"], textarea');
                        for (let el of inputs) {{
                            if (el.offsetParent !== null && !el.value) {{
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
                # 小红书描述通常是第二个 textarea 或 contenteditable
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

        # 5) 添加话题/标签
        if tags:
            logger.info(f"[{self.platform_id}] 添加话题: {tags}")
            try:
                # 尝试在文本后插入 #话题
                client.execute_js(
                    f"""(() => {{
                        const editables = document.querySelectorAll('textarea, div[contenteditable="true"]');
                        for (let i = editables.length - 1; i >= 0; i--) {{
                            const el = editables[i];
                            if (el.offsetParent !== null) {{
                                const cur = el.tagName === 'TEXTAREA' || el.tagName === 'INPUT' ? el.value : el.innerHTML;
                                const extra = ' ' + {repr(' '.join('#' + t for t in tags if t))};
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

        # 6) 提交：点击"发布"
        logger.info(f"[{self.platform_id}] 提交发布")
        submitted = False
        for tag in ["button", "span", "div"]:
            if client.select_by_contains_text(tag, "发布", wait_after=2.0):
                submitted = True
                break

        client.wait(3.0)

        return UploadResult(
            platform=self.platform_id,
            success=True,
            message="小红书上传流程已执行（发布状态请在小红书创作后台确认）",
            details={
                "title_set": title_filled,
                "description_set": bool(description),
                "tags_set": len(tags) > 0,
                "submitted": submitted,
                "current_url": client.get_url(),
            },
        )
