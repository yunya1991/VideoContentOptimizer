"""
CDP (Chrome DevTools Protocol) 客户端
连接 tencent-novnc-chromium-cdp Skill 部署的远程浏览器
通过 127.0.0.1:9223 控制 Chromium，实现无 API 平台的视频自动上传

使用方法::

    client = CDPClient(cdp_url="http://127.0.0.1:9223")
    await client.connect()
    await client.navigate("https://creator.douyin.com/")
    await client.wait(3)
    await client.fill_text("#title-input", "我的视频标题")
    await client.click("#submit-btn")
    await client.disconnect()
"""

import json
import urllib.request
import time
from typing import Dict, Optional, List, Any
from contextlib import asynccontextmanager

try:
    import websocket
except ImportError:
    websocket = None

from app.utils.logger import logger


class CDPError(Exception):
    """CDP 操作错误"""
    pass


class CDPClient:
    """
    Chrome DevTools Protocol 客户端。

    负责：
    - 发现可用页面 (target)
    - 通过 WebSocket 发送 CDP 指令
    - 执行页面导航、点击、输入、截图等操作
    """

    def __init__(
        self,
        cdp_url: str = "http://127.0.0.1:9223",
        timeout: int = 30,
        page_width: int = 1920,
        page_height: int = 1080,
    ):
        self.cdp_url = cdp_url.rstrip("/")
        self.timeout = timeout
        self.page_width = page_width
        self.page_height = page_height
        self._ws = None
        self._msg_id = 0
        self._target_id: Optional[str] = None

    # ─── 连接管理 ─────────────────────────────────────────────────────

    def connect(self, target_type: str = "page") -> "CDPClient":
        """
        连接到 CDP 浏览器并选取页面。
        阻塞式连接，失败抛出 CDPError。

        Args:
            target_type: 目标类型，默认 'page'

        Returns:
            self (支持链式调用)
        """
        if websocket is None:
            raise CDPError(
                "未安装 websocket-client，运行: pip install websocket-client"
            )

        pages = self._list_pages()
        if not pages:
            raise CDPError(f"CDP 无可用页面 ({self.cdp_url}/json)")

        page = pages[0]
        for p in pages:
            if p.get("type") == target_type:
                page = p
                break

        ws_url = page.get("webSocketDebuggerUrl")
        if not ws_url:
            raise CDPError(f"页面缺少 webSocketDebuggerUrl: {page}")

        logger.info(f"[CDP] 连接到: {page.get('title', '?')} -> {ws_url}")
        try:
            self._ws = websocket.create_connection(
                ws_url,
                header=["Origin: http://127.0.0.1:9223"],
                timeout=self.timeout,
            )
        except Exception as e:
            raise CDPError(f"WebSocket 连接失败: {e}")

        self._enable_domains()
        self._resize_viewport()
        self._target_id = page.get("id")
        return self

    def disconnect(self):
        """断开 CDP 连接"""
        try:
            if self._ws:
                self._ws.close()
        except Exception:
            pass
        self._ws = None
        self._target_id = None

    # ─── 浏览器操作 ───────────────────────────────────────────────────

    def navigate(self, url: str, wait_seconds: float = 2.0) -> Dict[str, Any]:
        """导航到指定 URL"""
        result = self._send("Page.navigate", {"url": url})
        if wait_seconds > 0:
            time.sleep(wait_seconds)
        return result

    def get_url(self) -> str:
        """获取当前页面 URL"""
        try:
            res = self._send(
                "Runtime.evaluate",
                {"expression": "location.href", "returnByValue": True},
            )
            return res.get("result", {}).get("value", "")
        except Exception:
            return ""

    def get_title(self) -> str:
        """获取当前页面标题"""
        try:
            res = self._send(
                "Runtime.evaluate",
                {"expression": "document.title", "returnByValue": True},
            )
            return res.get("result", {}).get("value", "")
        except Exception:
            return ""

    def wait(self, seconds: float):
        """等待指定秒数"""
        time.sleep(seconds)

    def wait_for_element(self, selector: str, max_wait: int = 15) -> bool:
        """
        等待元素出现（轮询式）。

        Args:
            selector: CSS 选择器
            max_wait: 最大等待秒数

        Returns:
            bool - 元素是否出现
        """
        deadline = time.time() + max_wait
        expr = f"!!document.querySelector({json.dumps(selector)})"
        while time.time() < deadline:
            try:
                res = self._send(
                    "Runtime.evaluate",
                    {"expression": expr, "returnByValue": True},
                )
                if res.get("result", {}).get("value") is True:
                    return True
            except Exception:
                pass
            time.sleep(0.5)
        return False

    def click(self, selector: str, wait_after: float = 1.0) -> bool:
        """点击指定元素"""
        js = f"""(() => {{
            const el = document.querySelector({json.dumps(selector)});
            if (!el) return {{ ok:false, reason:'not_found' }};
            el.click();
            return {{ ok:true }};
        }})()"""
        res = self._send("Runtime.evaluate", {"expression": js, "returnByValue": True})
        if wait_after > 0:
            time.sleep(wait_after)
        return res.get("result", {}).get("value", {}).get("ok") is True

    def fill_text(self, selector: str, text: str, wait_after: float = 0.5) -> bool:
        """在 input/textarea 中输入文本"""
        escaped = json.dumps(text)
        js = f"""(() => {{
            const el = document.querySelector({json.dumps(selector)});
            if (!el) return {{ ok:false, reason:'not_found' }};
            el.focus();
            el.value = {escaped};
            el.dispatchEvent(new Event('input', {{ bubbles:true }}));
            el.dispatchEvent(new Event('change', {{ bubbles:true }}));
            return {{ ok:true }};
        }})()"""
        res = self._send("Runtime.evaluate", {"expression": js, "returnByValue": True})
        if wait_after > 0:
            time.sleep(wait_after)
        return res.get("result", {}).get("value", {}).get("ok") is True

    def execute_js(self, expression: str, return_by_value: bool = True) -> Dict[str, Any]:
        """执行任意 JavaScript"""
        return self._send(
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": return_by_value},
        )

    def upload_file(self, selector: str, file_path: str, wait_after: float = 3.0) -> bool:
        """
        通过 input[type=file] 元素上传文件。

        Args:
            selector: 文件输入框选择器
            file_path: 本地文件绝对路径
            wait_after: 上传后等待秒数

        Returns:
            bool - 是否成功
        """
        # 1) 找到 DOM node
        doc_res = self._send("DOM.getDocument", {"depth": 1})
        root_id = doc_res.get("result", {}).get("root", {}).get("nodeId")
        if root_id is None:
            return False

        # 2) 查询 input[type=file]
        query_res = self._send(
            "DOM.querySelector",
            {"nodeId": root_id, "selector": selector},
        )
        node_id = query_res.get("result", {}).get("nodeId")
        if not node_id:
            logger.warning(f"[CDP] 未找到文件输入框: {selector}")
            return False

        # 3) 设置文件
        try:
            self._send(
                "DOM.setFileInputFiles",
                {"files": [file_path], "nodeId": node_id},
            )
            if wait_after > 0:
                time.sleep(wait_after)
            return True
        except Exception as e:
            logger.error(f"[CDP] 文件上传失败: {e}")
            return False

    def screenshot(self, output_path: Optional[str] = None) -> Optional[str]:
        """
        截取当前页面截图。

        Args:
            output_path: 输出文件路径（.png），None 时自动生成

        Returns:
            str - 保存的文件路径
        """
        res = self._send("Page.captureScreenshot", {"format": "png"})
        data = res.get("result", {}).get("data")
        if not data:
            return None

        if output_path is None:
            output_path = f"/tmp/cdp_screenshot_{int(time.time()*1000)}.png"

        import base64
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(data))
        return output_path

    def select_by_contains_text(self, tag: str, text: str, wait_after: float = 1.0) -> bool:
        """点击包含指定文本的元素（简单 xpath 替代）"""
        escaped = text.replace("'", "\\'")
        js = f"""(() => {{
            const elements = document.getElementsByTagName({json.dumps(tag)});
            for (let el of elements) {{
                if (el.textContent && el.textContent.includes('{escaped}')) {{
                    el.click();
                    return {{ ok:true }};
                }}
            }}
            return {{ ok:false, reason:'not_found' }};
        }})()"""
        res = self._send("Runtime.evaluate", {"expression": js, "returnByValue": True})
        if wait_after > 0:
            time.sleep(wait_after)
        return res.get("result", {}).get("value", {}).get("ok") is True

    def set_textarea_content(self, selector: str, text: str, wait_after: float = 0.5) -> bool:
        """向 contenteditable 或 textarea 输入长文本（支持富文本编辑器）"""
        escaped = json.dumps(text)
        js = f"""(() => {{
            const el = document.querySelector({json.dumps(selector)});
            if (!el) return {{ ok:false, reason:'not_found' }};
            el.focus();
            // 清空
            if (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT') {{
                el.value = {escaped};
            }} else {{
                el.innerHTML = {escaped};
            }}
            el.dispatchEvent(new Event('input', {{ bubbles:true }}));
            el.dispatchEvent(new Event('change', {{ bubbles:true }}));
            return {{ ok:true }};
        }})()"""
        res = self._send("Runtime.evaluate", {"expression": js, "returnByValue": True})
        if wait_after > 0:
            time.sleep(wait_after)
        return res.get("result", {}).get("value", {}).get("ok") is True

    # ─── 私有方法 ────────────────────────────────────────────────────

    def _list_pages(self) -> List[Dict[str, Any]]:
        """列出浏览器页面 (targets)"""
        try:
            req = urllib.request.urlopen(f"{self.cdp_url}/json", timeout=5)
            data = json.loads(req.read().decode("utf-8"))
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning(f"[CDP] 获取页面列表失败: {e}")
            return []

    def _enable_domains(self):
        """启用必要的 CDP domains"""
        for domain in ["Page", "DOM", "Runtime", "Network"]:
            try:
                self._send(f"{domain}.enable")
            except Exception as e:
                logger.warning(f"[CDP] {domain}.enable 失败: {e}")

    def _resize_viewport(self):
        """设置浏览器视口大小"""
        try:
            self._send(
                "Emulation.setDeviceMetricsOverride",
                {
                    "width": self.page_width,
                    "height": self.page_height,
                    "deviceScaleFactor": 1,
                    "mobile": False,
                },
            )
        except Exception:
            pass

    def _send(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        发送 CDP 命令并读取响应。

        Args:
            method: CDP 方法名
            params: 参数字典

        Returns:
            dict - 包含 id 和 result
        """
        if not self._ws:
            raise CDPError("WebSocket 未连接，先调用 connect()")

        self._msg_id += 1
        msg = json.dumps({"id": self._msg_id, "method": method, "params": params or {}})

        try:
            self._ws.send(msg)
        except Exception as e:
            raise CDPError(f"发送 CDP 消息失败: {e}")

        # 读响应，跳过 event 消息，直到拿到匹配 id 的响应
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            try:
                raw = self._ws.recv()
                if not raw:
                    continue
                resp = json.loads(raw)
                # 是事件消息，跳过
                if resp.get("method") and "id" not in resp:
                    continue
                if resp.get("id") == self._msg_id:
                    return resp
            except Exception as e:
                raise CDPError(f"读取 CDP 响应失败: {e}")

        raise CDPError(f"CDP 响应超时（method={method}）")


@asynccontextmanager
async def cdp_session(cdp_url: str = "http://127.0.0.1:9223"):
    """
    异步上下文管理器（内部使用阻塞 CDPClient，封装为 with 语法糖）。

    用法::

        async with cdp_session() as client:
            client.navigate("https://...")
    """
    client = CDPClient(cdp_url=cdp_url)
    client.connect()
    try:
        yield client
    finally:
        client.disconnect()


def is_cdp_available(cdp_url: str = "http://127.0.0.1:9223") -> bool:
    """快速检查 CDP 浏览器是否可用"""
    try:
        req = urllib.request.urlopen(f"{cdp_url}/json/version", timeout=3)
        data = json.loads(req.read().decode("utf-8"))
        return "Browser" in data
    except Exception:
        return False
