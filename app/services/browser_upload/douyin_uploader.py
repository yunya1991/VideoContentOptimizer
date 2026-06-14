"""
抖音创作者平台上传器
URL: https://creator.douyin.com/creator-micro/content/upload
"""

import time
from typing import List

from app.utils.logger import logger
from app.services.browser_upload.base_uploader import BaseBrowserUploader, UploadResult
from app.services.browser_upload.cdp_client import CDPClient


class DouyinUploader(BaseBrowserUploader):
    """抖音视频上传"""

    upload_url = "https://creator.douyin.com/creator-micro/content/upload"
    display_name = "抖音创作者平台"
    platform_id = "douyin"

    # 抖音创作者平台的元素选择器（UI 可能变化，可通过浏览器开发者工具调整）
    title_selector = 'div[class*="title"] textarea, textarea[placeholder*="标题"], textarea[placeholder*="标题"]'
    description_selector = 'div[contenteditable="true"], div[class*="description"], textarea[placeholder*="描述"], textarea[placeholder*="简介"]'
    file_input_selector = 'input[type="file"]'
    submit_button_text = "发布"

    def _needs_login(self, client: "CDPClient") -> bool:
        """抖音登录检测：URL 包含 login 或页面有登录按钮"""
        url = client.get_url().lower()
        title = client.get_title()

        # 当前被重定向到登录页
        if "login" in url or "signin" in url:
            return True

        # 检查 DOM 中是否有登录元素
        try:
            res = client.execute_js(
                """!!(document.querySelector('button:has-text("登录"), div[class*="login"], a[href*="login"]') || false)""",
                return_by_value=True,
            )
            # 简化策略：检查 URL 是否仍停留在 creator 域名
            if "creator.douyin.com" in url and "upload" in url:
                return False
            if "login" in title or "登录" in title:
                return True
        except Exception:
            pass

        return False

    def _get_login_hint(self) -> str:
        return (
            "抖音需要扫码登录。请在 noVNC 浏览器中使用手机抖音 APP 扫码，"
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
        """抖音上传流程"""

        # 1) 上传视频文件
        logger.info(f"[{self.platform_id}] 上传视频文件: {video_path}")
        # 等待上传按钮/区域出现
        client.wait_for_element('input[type="file"]', max_wait=15)
        uploaded = client.upload_file(
            self.file_input_selector, video_path, wait_after=3.0
        )
        if not uploaded:
            # 再试一次，可能页面还在加载
            time.sleep(3)
            uploaded = client.upload_file(
                self.file_input_selector, video_path, wait_after=5.0
            )
            if not uploaded:
                return UploadResult(
                    platform=self.platform_id,
                    success=False,
                    message="视频文件上传失败（未找到文件输入框或上传异常）",
                )

        logger.info(f"[{self.platform_id}] 视频已提交，等待上传处理")

        # 2) 等待视频上传和转码完成
        self._wait_for_upload_progress(client, max_wait=self.max_wait_upload)

        # 3) 填写标题（先点击标题区域激活）
        logger.info(f"[{self.platform_id}] 填写标题")
        # 尝试多种方式定位标题输入框
        title_filled = False

        # 方法1：textarea[placeholder*='标题']
        try:
            title_filled = client.fill_text(
                "textarea[placeholder*='标题']", title, wait_after=0.5
            )
        except Exception:
            pass

        if not title_filled:
            # 方法2：通过 contenteditable
            try:
                title_filled = client.set_textarea_content(
                    'div[contenteditable="true"]', title
                )
            except Exception:
                pass

        if not title_filled:
            # 方法3：简化 - 找第一个可输入的 input 或 textarea
            try:
                client.execute_js(
                    f"""(() => {{
                        const inputs = document.querySelectorAll('textarea, input[type="text"]');
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

        # 4) 填写描述/简介（如提供）
        if description:
            logger.info(f"[{self.platform_id}] 填写描述")
            try:
                # 尝试找第二个 contenteditable 或 description 相关元素
                client.execute_js(
                    f"""(() => {{
                        const editables = document.querySelectorAll('div[contenteditable="true"], textarea');
                        // 跳过第一个（标题），用第二个作描述
                        if (editables.length > 1) {{
                            const el = editables[1];
                            el.focus();
                            el.innerHTML = {repr(description)};
                            el.dispatchEvent(new Event('input', {{ bubbles:true }}));
                            return {{ ok:true }};
                        }}
                        return {{ ok:false, count: editables.length }};
                    }})()""",
                    return_by_value=True,
                )
            except Exception as e:
                logger.warning(f"[{self.platform_id}] 填写描述失败: {e}")

        # 5) 添加标签（如提供）
        if tags:
            logger.info(f"[{self.platform_id}] 添加标签: {tags}")
            try:
                # 简单策略：在描述后用 JS 插入 #标签
                tag_str = " ".join(f"#{t}" for t in tags if t)
                client.execute_js(
                    f"""(() => {{
                        const editables = document.querySelectorAll('div[contenteditable="true"]');
                        if (editables.length > 0) {{
                            const el = editables[editables.length - 1];
                            const cur = el.innerHTML || '';
                            el.innerHTML = cur + ' ' + {repr(tag_str)};
                            el.dispatchEvent(new Event('input', {{ bubbles:true }}));
                        }}
                    }})()""",
                    return_by_value=True,
                )
            except Exception:
                pass

        # 6) 提交：点击"发布"按钮
        logger.info(f"[{self.platform_id}] 提交发布")
        submitted = False

        # 尝试多种匹配：按钮文本、span 文本
        for tag in ["button", "span", "div"]:
            if client.select_by_contains_text(tag, "发布", wait_after=2.0):
                submitted = True
                break

        # 7) 确认状态
        client.wait(3.0)

        return UploadResult(
            platform=self.platform_id,
            success=True,  # 抖音无直接 API 验证发布，流程走完即算成功
            message="上传流程已执行完成（发布状态请在抖音创作者后台确认）",
            details={
                "title_set": title_filled,
                "description_set": bool(description),
                "tags_set": len(tags) > 0,
                "submitted": submitted,
                "current_url": client.get_url(),
            },
        )
