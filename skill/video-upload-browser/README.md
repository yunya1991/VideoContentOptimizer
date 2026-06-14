# video-upload-browser — 使用指南

## 目录

1. [快速开始](#1-快速开始)
2. [安装部署](#2-安装部署)
3. [配置管理](#3-配置管理)
4. [使用教程](#4-使用教程)
5. [平台上传指南](#5-平台上传指南)
6. [集成 VideoContentOptimizer](#6-集成-videocontentoptimizer)
7. [常见问题](#7-常见问题)
8. [与 tencent-novnc-chromium-cdp 的区别](#8-与-tencent-novnc-chromium-cdp-的区别)

---

## 1. 快速开始

### 1.1 一条命令安装

```bash
cd /path/to/VideoContentOptimizer/skill/video-upload-browser
bash scripts/setup.sh
```

### 1.2 启动服务

```bash
bash scripts/start.sh
```

### 1.3 检查状态

```bash
bash scripts/health-check.sh
```

### 1.4 访问 noVNC 完成登录

```
浏览器访问: http://<服务器IP>:6080/vnc.html
VNC 密码  : 见 ~/.config/chromium-video-upload/vnc_password
```

在 noVNC 中打开各平台，完成登录（扫码/账号密码）。

### 1.5 使用 VideoContentOptimizer API 上传

```bash
curl -X POST http://localhost:8080/api/v2/browser-upload/upload-file \
  -F "video=@my_video.mp4" \
  -F "title=我的AI优化视频" \
  -F "platforms=douyin,bilibili" \
  -F "description=视频简介" \
  -F "tags=AI,demo"
```

---

## 2. 安装部署

### 2.1 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Linux (Ubuntu 20.04+ / Debian 11+ / CentOS 8+) |
| 内存 | ≥ 2GB |
| 磁盘 | ≥ 2GB 可用空间 |
| 权限 | sudo 或 root |
| 网络 | 能访问外网（下载 Chromium / noVNC） |

### 2.2 安装步骤

#### 方式一：一键安装（推荐）

```bash
cd skill/video-upload-browser
bash scripts/setup.sh
```

脚本会自动完成:
- 安装 Xvfb / Chromium / x11vnc / noVNC
- 创建 systemd 服务文件
- 生成配置文件和 VNC 密码
- 配置持久化用户数据目录

#### 方式二：分步安装（可控）

```bash
# 1. 安装系统依赖
sudo apt-get update
sudo apt-get install -y xvfb chromium-browser x11vnc novnc

# 2. 手动运行启动脚本
bash scripts/start.sh

# 3. 健康检查
bash scripts/health-check.sh
```

### 2.3 使用 systemd 管理

```bash
# 启动
systemctl --user start video-upload-browser-xvfb
systemctl --user start video-upload-browser-chromium
systemctl --user start video-upload-browser-novnc

# 设置开机自启
systemctl --user enable video-upload-browser-xvfb
systemctl --user enable video-upload-browser-chromium
systemctl --user enable video-upload-browser-novnc

# 查看状态
systemctl --user status video-upload-browser-chromium

# 查看日志
journalctl --user -u video-upload-browser-chromium -f
```

（root 用户运行去掉 `--user`）

### 2.4 卸载

```bash
bash scripts/uninstall.sh
```

⚠️ 此操作会移除登录状态，谨慎操作。

---

## 3. 配置管理

### 3.1 配置文件

配置文件位置：`~/.config/chromium-video-upload/config.env

```bash
# 编辑配置
cat ~/.config/chromium-video-upload/config.env
```

### 3.2 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VUB_DISPLAY` | `:99` | Xvfb 虚拟显示器 |
| `VUB_CDP_PORT` | `9222` | Chromium CDP 端口 |
| `VUB_NOVNC_PORT` | `6080` | noVNC Web 端口 |
| `VUB_VNC_PORT` | `5900` | x11vnc VNC 端口 |
| `VUB_USER_DATA` | `~/.config/chromium-video-upload` | Chromium 用户数据目录 |
| `VUB_SCREEN_WIDTH` | `1920` | 屏幕宽度 |
| `VUB_SCREEN_HEIGHT` | `1080` | 屏幕高度 |
| `VUB_BIND_IP` | `127.0.0.1` | 绑定 IP（默认仅本地，更安全） |
| `VUB_VNC_PASSWORD` | 自动生成 | VNC 密码 |

### 3.3 修改配置示例

```bash
# 修改 CDP 端口为 9223
export VUB_CDP_PORT=9223
bash scripts/restart.sh

# 开放外网访问（⚠️ 需设置强密码）
export VUB_BIND_IP=0.0.0.0
bash scripts/restart.sh
```

---

## 4. 使用教程

### 4.1 通过 CDP API 手动操作

```bash
# 获取浏览器版本
curl http://127.0.0.1:9222/json/version

# 获取当前页面列表
curl http://127.0.0.1:9222/json
```

### 4.2 通过 noVNC 手动操作

1. 浏览器访问 `http://<服务器IP>:6080/vnc.html`
2. 输入 VNC 密码
3. 在远程浏览器中打开各平台，完成登录
4. 登录状态会自动保存，重启服务后依然可用

### 4.3 日志查看

```bash
# Xvfb 日志
tail -f skill/video-upload-browser/logs/xvfb.log

# Chromium 日志
tail -f skill/video-upload-browser/logs/chromium.log

# noVNC 日志
tail -f skill/video-upload-browser/logs/novnc.log
```

---

## 5. 平台上传指南

### 5.1 抖音创作者平台

**上传 URL**: `https://creator.douyin.com/

**首次使用步骤**:

1. 在 noVNC 中打开抖音创作者平台
2. 扫码登录（用抖音 APP 扫码
3. 登录成功后，VideoContentOptimizer 可以：
   - 自动调用 `BrowserUploadManager.upload_to_platforms(platforms=["douyin"], ...)`
   - 在视频文件
   - 自动填写标题、简介、标签
   - 点击发布

**API 调用**:

```bash
curl -X POST http://localhost:8080/api/v2/browser-upload/upload-file \
  -F "video=@my_video.mp4" \
  -F "title=我的视频标题" \
  -F "platforms=douyin"
```

### 5.2 小红书创作服务平台

**上传 URL**: `https://creator.xiaohongshu.com/`

**首次使用步骤**:

1. 在 noVNC 中打开小红书创作服务平台
2. 使用小红书 APP 扫码登录
3. 登录成功后，VideoContentOptimizer 自动上传

**注意事项**:
- 小红书对视频质量有要求（建议 ≤ 1GB
- 视频时长 支持视频封面

**API 调用**:

```bash
curl -X POST http://localhost:8080/api/v2/browser-upload/upload-file \
  -F "video=@my_video.mp4" \
  -F "title=我的视频标题" \
  -F "platforms=xiaohongshu"
```

### 5.3 哔哩哔哩创作中心

**上传 URL**: `https://member.bilibili.com/v2#/upload/video/frame`

**首次使用步骤**:

1. 在 noVNC 中打开 B 站
2. 扫码登录
3. 登录成功后，VideoContentOptimizer 自动上传

**API 调用**:

```bash
curl -X POST http://localhost:8080/api/v2/browser-upload/upload-file \
  -F "video=@my_video.mp4" \
  -F "title=我的视频" \
  -F "platforms=bilibili"
```

### 5.4 微信视频号助手

**上传 URL**: `https://channels.weixin.qq.com/platform/home

**首次使用步骤**:

1. 在 noVNC 中打开视频号
2. 用微信扫码登录
3. 登录成功后，VideoContentOptimizer 自动上传

**API 调用**:

```bash
curl -X POST http://localhost:8080/api/v2/browser-upload/upload-file \
  -F "video=@my_video.mp4" \
  -F "title=我的视频" \
  -F "platforms=weixin"
```

### 5.5 YouTube Studio

**上传 URL**: `https://studio.youtube.com/create/video`

**首次使用步骤**:

1. 在 noVNC 中打开 YouTube
2. 使用 Google 账号登录
3. 登录成功后，VideoContentOptimizer 自动上传

**API 调用**:

```bash
curl -X POST http://localhost:8080/api/v2/browser-upload/upload-file \
  -F "video=@my_video.mp4" \
  -F "title=My Video Title" \
  -F "description=Video Description" \
  -F "platforms=youtube"
```

### 5.6 TikTok Creator Center

**上传 URL**: `https://www.tiktok.com/tiktokstudio/upload

**首次使用步骤**:

1. 在 noVNC 中打开 TikTok
2. 完成登录
3. 登录成功后，VideoContentOptimizer 自动上传

**API 调用**:

```bash
curl -X POST http://localhost:8080/api/v2/browser-upload/upload-file \
  -F "video=@my_video.mp4" \
  -F "title=My Video Title" \
  -F "platforms=tiktok"
```

### 5.7 多平台同时发布

```bash
curl -X POST http://localhost:8080/api/v2/browser-upload/upload-file \
  -F "video=@my_video.mp4" \
  -F "title=My Video Title" \
  -F "platforms=douyin,xiaohongshu,bilibili,weixin,youtube,tiktok"
```

---

## 6. 集成 VideoContentOptimizer

### 6.1 自动集成

VideoContentOptimizer 项目默认已包含 browser_upload 模块，无需额外安装。

### 6.2 Python SDK 调用示例

```python
from app.services.browser_upload.manager import BrowserUploadManager

# 初始化
mgr = BrowserUploadManager(cdp_url="http://127.0.0.1:9222")

# 查看支持平台
for p in mgr.list_platforms():
    print(p["platform_id"])

# 健康检查
hc = mgr.health_check()
print(f"CDP 可用: {hc['cdp_available']}")

# 上传视频
result = mgr.upload_to_platforms(
    video_path="/tmp/my_video.mp4,
    title="我的视频",
    platforms=["douyin", "bilibili"],
    description="视频简介",
    tags=["AI", "demo"]
)

print(f"成功 {result['success']}/{result['total']}")
for r in result["results"]:
    print(f"  {r['platform']}: {'成功' if r.get('success') else '失败'} - {r.get('message', '')}")
```

### 6.3 HTTP API 调用

所有 `/api/v2/browser-upload/*` 接口：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/platforms` | 列出支持平台 |
| GET | `/health` | 健康检查 |
| POST | `/upload` | 基于本地文件路径上传 |
| POST | `/upload-file` | 上传视频文件 |
| POST | `/session-check` | 检查浏览器会话 |

---

## 7. 常见问题

### Q1: noVNC 无法连接？

运行 `bash scripts/health-check.sh` 检查三个组件状态。

### Q2: 登录状态丢失？

- 确保 `~/.config/chromium-video-upload/` 目录存在且有权限
- 不要删除 User Data 目录

### Q3: 视频上传卡住？

检查：
1. 视频大小限制（抖音 ≤ 1GB，其他平台类似）
2. 网络连接是否正常
3. 平台是否有临时维护

### Q4: VNC 密码忘记？

```bash
cat ~/.config/chromium-video-upload/vnc_password
```

### Q5: CDP 端口被占用？

```bash
lsof -i :9222
# 或
netstat -tlnp | grep 9222
```

### Q6: 如何修改端口？

```bash
export VUB_CDP_PORT=9223
bash scripts/restart.sh
```

然后在 VideoContentOptimizer 的 `.env` 中同步更新：

```
CDP_URL=http://127.0.0.1:9223
```

### Q7: 浏览器崩溃？

查看 Chromium 日志：

```bash
tail -100 ~/.config/chromium-video-upload/.../logs/chromium.log
```

常见原因：
- 内存不足（需要 ≥ 2GB）
- /tmp 空间不足
- 权限问题

### Q8: 如何更新 Chromium？

```bash
# Ubuntu/Debian
sudo apt-get update && sudo apt-get install -y chromium-browser

# 重启服务
bash scripts/restart.sh
```

---

## 8. 与 tencent-novnc-chromium-cdp 的区别

| 项目 | tencent-novnc-chromium-cdp | **video-upload-browser（本 Skill）** |
|------|-----------------------------|---------------------------------|
| 定位 | 通用远程浏览器 | **VideoContentOptimizer 专用** |
| 目标 | 通用用途 | **专为视频上传优化** |
| CDP 端口 | 9223 | **9222** |
| 用户数据 | 临时目录 | **持久化存储，自动保存登录状态** |
| 集成接口 | 无 | **深度集成 VideoContentOptimizer** |
| 文档 | 简单 | **完整中文文档** |
| 平台上传器 | 无 | **6 个平台上传器** |
| 维护 | 外部依赖 | **项目内维护** |

---

## 9. 安全提示

1. **默认仅绑定 `127.0.0.1`，更安全
2. 如需开放外网访问，设置强密码
3. 通过 SSH 隧道访问更安全
4. 不要备份或上传 `~/.config/chromium-video-upload/` 目录
5. 定期备份密码文件不要提交到 Git 仓库

---

## 10. License

MIT License — 与 VideoContentOptimizer 一致
