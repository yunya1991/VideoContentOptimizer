---
name: video-ai-optimizer
description: "视频AI优化器技能，支持多TTS引擎配音、多LLM提供商、Redis任务存储、字幕烧录、upload-post.com跨平台发布全链路。触发词：视频优化、AI视频处理、短视频优化、视频重生成、视频分析、TTS配音、字幕生成、视频发布、批量视频处理、Whisper转录、DeepSeek、Anthropic、upload-post"
---

# 视频AI优化器技能

## 场景速查卡（先看这里）

| 我想做的事 | 用哪个功能 | 最少需要配置什么 |
|---|---|---|
| 分析一个视频的内容和质量 | `/api/v2/analyzer/analyze` | `LLM_API_KEY` |
| 优化文案、生成爆款标题 | `/api/v2/optimizer/optimize` | `LLM_API_KEY` |
| 给视频换一段 AI 配音 | 重生成 + `TTS_VOICE_NAME` | 默认 edge 免费，无需 Key |
| 自动烧录中文字幕 | `SUBTITLE_ENABLED=true` | 无需额外 Key |
| 发布到 TikTok / YouTube | `UPLOAD_POST_ENABLED=true` | `UPLOAD_POST_API_KEY` |
| 同时处理 10 个以上视频 | `/api/v2/analyzer/batch` | `LLM_API_KEY` |
| 切换到 Claude / Qwen | `LLM_MODEL=anthropic:xxx` | `ANTHROPIC_API_KEY` |

---

## 快速导航

**用户需求 → 操作流程**

- **部署安装** → 环境准备 → Docker部署 → 服务启动
- **视频分析** → 上传视频 → AI分析 → 查看报告
- **智能优化** → 获取建议 → 确认优化 → 重生成视频
- **TTS 配音** → 选择引擎 → 配置参数 → 生成音频
- **字幕生成** → 启用字幕 → 时间轴构建 → 烧录输出
- **批量处理** → 批量上传 → 并行处理 → 结果汇总
- **跨平台发布** → 配置 API Key → 选择平台 → 一键发布
- **配置管理** → 环境配置 → API密钥 → 平台设置
- **故障排查** → 日志查看 → 问题诊断 → 解决方案

---

## AI 使用指南

### 场景判断

当用户提到以下关键词时，加载本技能：

- 视频优化、AI视频处理、短视频优化
- 视频重生成、视频分析、智能剪辑
- TTS、配音、字幕、字幕时间轴
- 视频发布、upload-post、跨平台发布
- 批量视频处理、Whisper转录
- DeepSeek、OpenAI、Anthropic、Qwen、多模型

---

## 操作流程

### 1. 环境准备和部署

```bash
# 检查系统环境
python --version   # 3.10+
ffmpeg -version    # 任意版本

# 安装依赖
pip install -r requirements.txt

# 最小依赖（edge TTS 免费）
# edge-tts>=6.1.0 已包含在 requirements.txt
# imageio-ffmpeg 用于自动查找 FFmpeg（pip install imageio-ffmpeg）

# 可选依赖（付费 TTS）
# pip install azure-cognitiveservices-speech  # Azure
# pip install google-generativeai              # Gemini
# pip install anthropic                        # Anthropic Claude

# Docker 一键启动
docker-compose up -d
```

### 2. LLM 提供商配置

支持 6 种提供商，统一接口 `LLMClient`：

```bash
# .env 配置示例

# DeepSeek（默认，低成本中文优化）
LLM_PROVIDER=deepseek
LLM_API_KEY=sk-xxx
LLM_MODEL=deepseek-chat

# OpenAI
LLM_PROVIDER=openai
LLM_API_KEY=sk-xxx
LLM_MODEL=gpt-4o-mini

# Anthropic Claude（需安装 pip install anthropic）
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-xxx
LLM_MODEL=claude-sonnet-4-6

# Qwen / 通义千问（阿里云）
LLM_PROVIDER=qwen
LLM_API_KEY=sk-xxx
LLM_MODEL=qwen-plus

# SiliconFlow（国内，免费额度）
LLM_PROVIDER=siliconflow
LLM_API_KEY=sk-xxx
LLM_MODEL=Qwen/Qwen2.5-7B-Instruct

# 模型前缀路由（一行切换引擎，无需改 LLM_PROVIDER）
LLM_MODEL=anthropic:claude-opus-4-7    # 自动切换到 anthropic
LLM_MODEL=qwen:qwen-plus               # 自动切换到 qwen
```

### 3. TTS 配音配置

支持 5 种 TTS 引擎，通过 `voice_name` 前缀路由：

```bash
# .env 配置示例

# edge TTS（免费默认，中文效果好）
TTS_VOICE_NAME=edge:zh-CN-XiaoxiaoNeural
TTS_VOICE_RATE=0        # 语速：0=原速，+10=加速10%，-10=减速10%
TTS_VOICE_VOLUME=1.0    # 音量倍数

# SiliconFlow CosyVoice2（国内，有免费额度）
TTS_VOICE_NAME=siliconflow:anna
SILICONFLOW_API_KEY=sk-xxx

# Azure Speech（高质量付费）
TTS_VOICE_NAME=azure:zh-CN-XiaoxiaoNeural
AZURE_SPEECH_KEY=xxx
AZURE_SPEECH_REGION=eastus

# Gemini TTS
TTS_VOICE_NAME=gemini:Zephyr
GEMINI_API_KEY=xxx

# MiMo TTS（小米）
TTS_VOICE_NAME=mimo:female_1
MIMO_API_KEY=xxx
```

**常用 edge TTS 中文音色：**
- `zh-CN-XiaoxiaoNeural` — 女声，活泼
- `zh-CN-YunxiNeural` — 男声，通用
- `zh-CN-XiaoyiNeural` — 女声，温柔
- `zh-TW-HsiaoChenNeural` — 台湾普通话

### 4. 字幕配置

```bash
# .env 配置示例

SUBTITLE_ENABLED=true         # 启用字幕烧录
SUBTITLE_FONT_SIZE=36         # 字体大小
SUBTITLE_FONT_COLOR=white     # 字体颜色
SUBTITLE_POSITION=bottom      # 位置：bottom / top / center
```

字幕流程：
1. TTS 生成音频
2. `SubMaker.from_timed_text()` 按字符比例构建时间轴（任意引擎）
   或 `SubMaker.from_edge_tts_cues()` 从 edge_tts 词边界精确构建
3. 输出标准 SRT 文件（UTF-8 BOM）
4. FFmpeg `subtitles` 滤镜烧录进视频

### 5. 跨平台发布配置

通过 [upload-post.com](https://upload-post.com) API 实现跨平台发布：

```bash
# .env 配置示例

UPLOAD_POST_ENABLED=true
UPLOAD_POST_API_KEY=xxx          # upload-post.com API Key
UPLOAD_POST_USERNAME=your_user   # 你的用户名
UPLOAD_POST_PLATFORMS=tiktok,youtube,instagram  # 默认发布平台
```

**支持平台：**
| 本项目名称 | upload-post.com 标识 | 说明 |
|---|---|---|
| `douyin` | `tiktok` | 抖音 = TikTok 国内版，自动映射 |
| `tiktok` | `tiktok` | TikTok 国际版 |
| `youtube` | `youtube` | YouTube |
| `instagram` | `instagram` | Instagram |
| `facebook` | `facebook` | Facebook |
| `twitter` | `twitter` | Twitter / X |
| `linkedin` | `linkedin` | LinkedIn |
| `xiaohongshu` | — | 暂不支持，自动跳过 |
| `weixin` | — | 暂不支持，自动跳过 |

### 6. 视频分析流程

```bash
# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8080 &
streamlit run webui/main.py &

# API 调用示例
curl -X POST http://localhost:8080/api/v2/analyzer/analyze \
  -F "file=@video.mp4" \
  -F "intent_category=教程"

# 查询结果
curl http://localhost:8080/api/v2/analyzer/result/{task_id}
```

### 7. 任务状态管理

任务状态使用 `TaskStore` 双后端存储（自动 TTL 清理）：

```bash
# .env 配置（可选 Redis，不配则自动用内存）
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

- **Redis 可用**：任务状态持久化，重启不丢失
- **Redis 不可用**：自动降级到内存存储，TTL=1小时，超 10000 条自动淘汰最旧

### 8. 故障排查

```bash
# FFmpeg 找不到
pip install imageio-ffmpeg   # 自动包含 FFmpeg 二进制
# 或设置环境变量
export FFMPEG_PATH=/usr/bin/ffmpeg

# Anthropic 导入失败
pip install anthropic

# edge_tts 失败
pip install edge-tts
# 或更新：pip install --upgrade edge-tts

# LLM API 调用失败
# 检查 LLM_API_KEY 是否设置，确认 provider 名称正确

# TTS 文件为空
# 检查 TEMP_DIR 目录权限
# 检查网络（edge TTS 需要联网）

# 查看服务日志
tail -f logs/app.log
```

---

## 交互示例

### 示例 1：配置 Anthropic Claude

**用户**："我想换成 Claude 模型"

**执行流程**：
1. 安装 SDK：`pip install anthropic`
2. 在 `.env` 中设置：
   ```
   LLM_PROVIDER=anthropic
   ANTHROPIC_API_KEY=sk-ant-xxx
   LLM_MODEL=claude-sonnet-4-6
   ```
   或使用模型前缀一行切换：
   ```
   LLM_MODEL=anthropic:claude-opus-4-7
   ```
3. 重启服务

### 示例 2：生成带字幕的视频

**用户**："重生成视频，需要字幕"

**执行流程**：
1. 在 `.env` 中启用：`SUBTITLE_ENABLED=true`
2. 调用重生成接口，系统自动：
   - TTS 生成音频
   - `SubMaker` 构建字幕时间轴
   - FFmpeg 将字幕烧录进视频
3. 返回带字幕的最终视频

### 示例 3：发布到 TikTok + YouTube

**用户**："把这个视频发布到抖音和 YouTube"

**执行流程**：
1. 确认 `.env` 配置了 `UPLOAD_POST_API_KEY`
2. 调用 `POST /api/v2/regenerator/publish`：
   ```json
   {
     "video_path": "/path/to/video.mp4",
     "title": "视频标题",
     "platforms": ["douyin", "youtube"]
   }
   ```
3. 系统自动映射 `douyin→tiktok`，发布到两平台
4. 返回 `request_id`，可用于查询发布状态

---

## 使用限制与规格

### 视频文件
| 限制项 | 规格 | 说明 |
|---|---|---|
| 最大文件大小 | 500 MB | 由 `MAX_VIDEO_SIZE_MB` 控制，可调大 |
| 支持格式 | mp4 / mov / avi / mkv | 由 `ALLOWED_EXTENSIONS` 控制 |
| 推荐时长 | ≤ 30 分钟 | 更长的视频 Whisper 转录耗时显著增加 |
| 1 小时视频转录 | ~8-15 分钟（base 模型，CPU） | 用 `WHISPER_MODEL_SIZE=small` 可提升精度，用 `cuda` 设备可大幅加速 |
| 复杂特效视频 | 正常处理 | 本工具只处理音频轨和文案，不修改特效层 |

### LLM API 调用限制
| Provider | 免费额度 | 推荐并发 | 超限行为 |
|---|---|---|---|
| DeepSeek | 按量计费，价格低 | 5-10 并发 | 返回 429，日志报错 |
| OpenAI | 按量计费 | 3-5 并发 | 返回 429，日志报错 |
| Anthropic | 按量计费 | 3-5 并发 | 返回 429，日志报错 |
| Qwen / 通义 | 每月有免费额度 | 3-5 并发 | 返回 429，日志报错 |
| SiliconFlow | 每日有免费额度 | 2-3 并发 | 返回 429，日志报错 |

> API 超限时系统会在日志中记录错误（`logs/app.log`），不会静默丢弃，但不自动重试。批量处理建议设置 `PARALLEL_WORKERS=2`。

### TTS 文本长度
| 引擎 | 单次最大字符数 | 超长处理 |
|---|---|---|
| edge | ~3000 字 | 自动分段合并 |
| azure | ~3000 字 | 自动分段合并 |
| siliconflow | ~500 字 | 超出会被截断，建议先分段 |
| gemini | ~5000 字 | API 限制 |
| mimo | ~1000 字 | API 限制 |

### 跨平台发布限制
- 标题最长 **2200 字符**（自动截断）
- 视频上传超时设置为 **300 秒**（大文件建议网络稳定时发布）
- 小红书、微信视频号：upload-post.com **暂不支持**，调用会跳过并在日志中提示

---

## 快速排查

| 现象 | 最可能的原因 | 解决方法 |
|---|---|---|
| 启动报错 `生产环境禁止使用默认弱密钥` | SECRET_KEY / JWT_SECRET 未改 | 运行 `python -c "import secrets; print(secrets.token_hex(32))"` 生成并填入 `.env` |
| 分析接口返回 500 | LLM_API_KEY 未设置或余额不足 | 检查 `.env` 中 `LLM_API_KEY`，查看 `logs/app.log` |
| TTS 生成的文件为空 | edge_tts 网络不通 | 检查网络，或换 `siliconflow:anna` 引擎 |
| 字幕烧录后视频没有字幕 | `SUBTITLE_ENABLED` 未设为 `true` | 在 `.env` 中设置 `SUBTITLE_ENABLED=true` 后重启 |
| 发布返回 503 | `UPLOAD_POST_ENABLED=false` | 在 `.env` 中设置 `UPLOAD_POST_ENABLED=true` 并填入 `UPLOAD_POST_API_KEY` |
| 发布返回 400 "所有平台均不支持" | 只填了 xiaohongshu / weixin | 改用 `tiktok` / `youtube` 等支持的平台 |
| Whisper 转录很慢 | 使用 CPU + base 模型 | 设置 `WHISPER_DEVICE=cuda`（需 GPU）或 `WHISPER_MODEL_SIZE=tiny` |
| `anthropic` 报 ImportError | 未安装 SDK | `pip install anthropic` |
| FFmpeg 找不到 | 系统未安装或路径错误 | `pip install imageio-ffmpeg` 或设置 `FFMPEG_PATH` |
| 批量处理中途停止 | 单个视频失败导致中断 | 查看 `logs/app.log`，失败的视频会被跳过并记录 |

---

## 完整 .env 配置模板

```bash
# ── LLM ────────────────────────────────────────
LLM_PROVIDER=deepseek           # deepseek / openai / anthropic / qwen / siliconflow
LLM_API_KEY=sk-xxx
LLM_MODEL=deepseek-chat
ANTHROPIC_API_KEY=              # 仅 anthropic provider 需要

# ── TTS ────────────────────────────────────────
TTS_VOICE_NAME=edge:zh-CN-XiaoxiaoNeural
TTS_VOICE_RATE=0
TTS_VOICE_VOLUME=1.0
AZURE_SPEECH_KEY=
AZURE_SPEECH_REGION=eastus
SILICONFLOW_API_KEY=
GEMINI_API_KEY=
MIMO_API_KEY=

# ── 字幕 ───────────────────────────────────────
SUBTITLE_ENABLED=false
SUBTITLE_FONT_SIZE=36
SUBTITLE_FONT_COLOR=white
SUBTITLE_POSITION=bottom

# ── 平台发布 ───────────────────────────────────
UPLOAD_POST_ENABLED=false
UPLOAD_POST_API_KEY=
UPLOAD_POST_USERNAME=
UPLOAD_POST_PLATFORMS=tiktok

# ── 系统 ───────────────────────────────────────
FFMPEG_PATH=/usr/bin/ffmpeg
TEMP_DIR=/tmp/video_optimizer
WHISPER_MODEL_SIZE=base

# ── 存储（Redis 可选，不配则内存模式）────────────
REDIS_HOST=localhost
REDIS_PORT=6379
```
