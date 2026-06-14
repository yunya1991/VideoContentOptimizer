# video-upload-browser — 视频上传远程浏览器

**版本**: 1.0.0  
**用途**: VideoContentOptimizer 专用远程浏览器环境，用于无 API 平台（抖音/小红书/B站/微信视频号/YouTube/TikTok）的视频自动上传。

---

## 概述

本 Skill 在 Linux 服务器上部署一个轻量级远程浏览器环境（Xvfb + Chromium + noVNC + CDP），使 AI Agent 可以通过 Chrome DevTools Protocol 自动操作浏览器完成视频上传流程。

**组件**:
- **Xvfb** — 虚拟显示器，使 Chromium 在无图形环境中运行
- **Chromium** — 浏览器本体，启用 CDP 调试端口
- **noVNC** — 轻量级 HTML5 VNC 客户端，供用户通过浏览器查看和操作
- **系统服务** — 开机自启，崩溃自动重启

---

## 快速开始

### 1. 安装

```bash
cd /path/to/skill/video-upload-browser
bash scripts/setup.sh
```

脚本会自动：
1. 安装 Xvfb、Chromium、x11vnc、novnc、websockify
2. 创建 systemd 服务文件（`video-upload-browser@xvfb.service / @chromium.service / @novnc.service）
3. 配置用户数据目录，持久化登录状态

### 2. 启动

```bash
bash scripts/start.sh
```

启动后三个组件均为 daemon 运行：

| 组件 | 端口 | 说明 |
|------|------|------|
| Xvfb | DISPLAY=:99 | 虚拟显示器 |
| Chromium | 9222 (CDP) | 浏览器调试端口 |
| noVNC | 6080 | Web VNC 访问 |
| x11vnc | 5900 | VNC 协议端口 |

### 3. 使用

**a. 在浏览器中查看远程浏览器**

访问 `http://<服务器IP>:6080/vnc.html`

首次使用时，请在 noVNC 中完成各平台的登录（扫码/账号密码）。登录状态会保存在 `~/.config/chromium-video-upload/` 中，重启浏览器后依然保留。

**b. 通过 CDP API 控制**

```bash
# 检查 CDP 是否可用
curl http://127.0.0.1:9222/json/version

# 检查页面列表
curl http://127.0.0.1:9222/json
```

**c. 在 VideoContentOptimizer 中调用**

```python
from app.services.browser_upload.manager import BrowserUploadManager

mgr = BrowserUploadManager(cdp_url="http://127.0.0.1:9222")
result = mgr.upload_to_platforms(
    video_path="/tmp/my_video.mp4",
    title="AI优化视频",
    platforms=["douyin", "bilibili"],
    description="视频简介",
    tags=["AI", "demo"],
)
```

**d. 通过 VideoContentOptimizer API 上传**

```bash
curl -X POST http://localhost:8080/api/v2/browser-upload/upload-file \
  -F "video=@my_video.mp4" \
  -F "title=我的AI优化视频" \
  -F "platforms=douyin,bilibili" \
  -F "description=视频简介" \
  -F "tags=AI,demo"
```

---

## 配置

### 环境变量（可选）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VUB_DISPLAY` | `:99` | Xvfb 虚拟显示器编号 |
| `VUB_CDP_PORT` | `9222` | Chromium CDP 端口 |
| `VUB_NOVNC_PORT` | `6080` | noVNC Web 端口 |
| `VUB_VNC_PORT` | `5900` | x11vnc VNC 端口 |
| `VUB_USER_DATA` | `~/.config/chromium-video-upload` | Chromium 用户数据目录 |
| `VUB_VNC_PASSWORD` | 自动生成 | VNC 访问密码 |
| `VUB_SCREEN_WIDTH` | `1920` | 屏幕宽度 |
| `VUB_SCREEN_HEIGHT` | `1080` | 屏幕高度 |

### VideoContentOptimizer 集成配置

在项目的 `.env` 中添加：

```bash
# video-upload-browser Skill
CDP_ENABLED=true
CDP_URL=http://127.0.0.1:9222
CDP_VIEWPORT_WIDTH=1920
CDP_VIEWPORT_HEIGHT=1080
CDP_UPLOAD_TIMEOUT=300
```

---

## 常见问题

### Q1: noVNC 无法连接？

检查三个组件是否都在运行：

```bash
bash scripts/health-check.sh
```

如果某个组件挂了，使用 `systemctl restart video-upload-browser@xvfb` 等命令重启。

### Q2: 登录状态丢失？

Chromium 用户数据保存在 `~/.config/chromium-video-upload/`。确保目录存在且有权限。不要用 `rm -rf` 清理该目录。

### Q3: 如何重新登录某个平台？

1. 访问 noVNC (`http://<服务器IP>:6080/vnc.html`)，在浏览器中手动打开对应平台网址，重新登录即可。

### Q4: CDP 端口被占用？

```bash
lsof -i :9222
```

### Q5: VNC 密码忘记？

```bash
cat ~/.config/chromium-video-upload/vnc_password
```

---

## 安全说明

- **VNC 访问**: 默认绑定到 `127.0.0.1`（仅本地访问），如需开放外网访问，请在 `scripts/setup.sh` 中将 `VUB_BIND_IP` 改为 `0.0.0.0`，并确保设置强密码。生产环境建议：使用 HTTPS + 反向代理 + 强密码。
- **CDP 端口**: 默认绑定 `127.0.0.1`，不会暴露到外网。
- **登录凭证**: Chromium 用户数据目录包含各平台的登录 cookie，请不要备份或上传到公开仓库。

---

## 与 tencent-novnc-chromium-cdp 的区别

| 项目 | tencent-novnc-chromium-cdp | **video-upload-browser（本 Skill） |
|------|-----------------------------|---------------------------------|
| 用途 | 通用远程浏览器 | **VideoContentOptimizer 专用** |
| CDP 端口 | 9223 | **9222** |
| 用户数据目录 | 临时 | **持久化，支持多平台登录** |
| 集成接口 | 无 | **/api/v2/browser-upload/* API** |
| 平台支持 | 通用 | **抖音/小红书/B站/微信视频号/YouTube/TikTok** |
| 文档 | 简单 | **完整集成指南** |
| 视频上传器 | 无 | **6个平台上传器** |
