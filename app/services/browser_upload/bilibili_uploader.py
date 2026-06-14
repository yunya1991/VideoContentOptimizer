"""
B站（哔哩哔哩）投稿中心上传器
URL: https://member.bilibili.com/v2#/upload/video/frame
"""

import time
from typing import List

from app.utils.logger import logger
from app.services.browser_upload.base_uploader import BaseBrowserUploader, UploadResult
from app.services.browser_upload.cdp_client import CDPClient


class BilibiliUploader(BaseBrowserUploader):
    """B站视频上传"""

    upload_url = "https://member.bilibili.com/v2#/upload/video/frame"
    display_name = "哔哩哔哩创作中心"
    platform_id = "bilibili"

    file_input_selector = 'input[type="file"]'
    submit_button_text = "立即投稿"

    def _needs_login(self, client: "CDPClient") -> bool:
        url = client.get_url().lower()
        title = client.get_title()

        if "passport" in url or "login" in url or "signin" in url:
            return True
        if "登录" in title:
            return True

        # 如果 URL 仍在投稿中心，则 OK
        if "member.bilibili.com" in url:
            return False
        return False

    def _get_login_hint(self) -> str:
        return (
            "B站需要登录。请在 noVNC 浏览器中完成扫码/账号登录，"
            "完成登录后重新调用上传接口。"
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
        """B站视频上传流程"""

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

        # 2) 等待上传和转码
        logger.info(f"[{self.platform_id}] 等待视频处理")
        self._wait_for_upload_progress(client, max_wait=self.max_wait_upload)

        # 3) 填写标题
        logger.info(f"[{self.platform_id}] 填写标题")
        title_filled = False
        for sel in [
            "input[placeholder*='标题']",
            "input[placeholder*='标题']",
            "textarea[placeholder*='标题']",
            "textarea[placeholder*='标题']",
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

        # 4) 选择分区（B站必填）：默认选择"生活-其他"
        # 由于分区选择复杂，此处仅尝试选择第一个可用分区选项
        try:
            client.execute_js(
                """(() => {
                    // 找到下拉选项中第一个可选的分区
                    const options = document.querySelectorAll('li, [role="option"], .bili-select-option');
                    for (let opt of options) {
                        if (opt.offsetParent !== null) {
                            opt.click();
                            return { ok:true };
                        }
                    }
                    return { ok:false };
                })()""",
                return_by_value=True,
            )
        except Exception:
            pass

        # 5) 填写描述/简介
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

        # 6) 标签
        if tags:
            logger.info(f"[{self.platform_id}] 添加标签")
            try:
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

        # 7) 提交
        logger.info(f"[{self.platform_id}] 提交投稿")
        submitted = False
        for btn_text in ["立即投稿", "投稿", "提交", "发布"]:
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
            message="B站投稿流程已执行（请在B站创作中心确认状态）",
            details={
                "title_set": title_filled,
                "description_set": bool(description),
                "tags_set": len(tags) > 0,
                "submitted": submitted,
                "current_url": client.get_url(),
            },
        )
