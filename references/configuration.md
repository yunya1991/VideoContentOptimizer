# 配置说明文档

所有配置通过 `.env` 文件（Pydantic Settings）注入，无需改代码。

---

## LLM 配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LLM_PROVIDER` | `deepseek` | 提供商：`deepseek` / `openai` / `anthropic` / `qwen` / `dashscope` / `siliconflow` |
| `LLM_API_KEY` | `""` | API Key（deepseek/openai/qwen/siliconflow 使用） |
| `LLM_BASE_URL` | `None` | 自定义 base URL（留空使用各 provider 默认值） |
| `LLM_MODEL` | `deepseek-chat` | 模型名。支持前缀路由：`anthropic:claude-opus-4-7` 会覆盖 LLM_PROVIDER |
| `ANTHROPIC_API_KEY` | `""` | Anthropic Claude 专用 Key（LLM_PROVIDER=anthropic 时使用） |

**模型前缀路由示例：**
```bash
LLM_MODEL=anthropic:claude-opus-4-7    # provider 自动切换为 anthropic
LLM_MODEL=qwen:qwen-plus               # provider 自动切换为 qwen
LLM_MODEL=deepseek:deepseek-chat       # 明确指定（同样有效）
```

---

## TTS 配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `TTS_VOICE_NAME` | `edge:zh-CN-XiaoxiaoNeural` | `engine:voice_id` 格式，引擎前缀决定路由 |
| `TTS_VOICE_RATE` | `0` | 语速百分比，0=原速，+10=加速10%，-10=减速10% |
| `TTS_VOICE_VOLUME` | `1.0` | 音量倍数（1.0=原始） |
| `AZURE_SPEECH_KEY` | `""` | Azure Speech SDK Key |
| `AZURE_SPEECH_REGION` | `eastus` | Azure 区域 |
| `SILICONFLOW_API_KEY` | `""` | SiliconFlow CosyVoice2 Key |
| `GEMINI_API_KEY` | `""` | Gemini TTS Key |
| `MIMO_API_KEY` | `""` | 小米 MiMo TTS Key |

**支持的 TTS 引擎：**

| 前缀 | 引擎 | 费用 | 典型 voice_id |
|------|------|------|---------------|
| `edge:` | edge_tts | **免费** | `zh-CN-XiaoxiaoNeural` |
| `azure:` | Azure Speech SDK | 付费 | `zh-CN-XiaoxiaoNeural` |
| `siliconflow:` | CosyVoice2 | 有免费额度 | `anna` |
| `gemini:` | Gemini TTS | 按量计费 | `Zephyr` |
| `mimo:` | 小米 MiMo | 按量计费 | `female_1` |

---

## 字幕配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SUBTITLE_ENABLED` | `false` | 是否在重生成时自动烧录字幕 |
| `SUBTITLE_FONT_SIZE` | `36` | 字幕字体大小（像素） |
| `SUBTITLE_FONT_COLOR` | `white` | 字体颜色（CSS 颜色名或 hex） |
| `SUBTITLE_POSITION` | `bottom` | 字幕位置：`bottom` / `top` / `center` |

---

## 平台发布配置（upload-post.com）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `UPLOAD_POST_ENABLED` | `false` | 是否启用平台发布功能 |
| `UPLOAD_POST_API_KEY` | `""` | upload-post.com API Key |
| `UPLOAD_POST_USERNAME` | `""` | upload-post.com 用户名 |
| `UPLOAD_POST_PLATFORMS` | `["tiktok"]` | 默认发布平台列表（逗号分隔：`tiktok,youtube`） |

**平台映射：**
- `douyin` → `tiktok`（自动映射）
- `xiaohongshu`, `weixin` → 不支持，自动跳过并记录日志

---

## Whisper 配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `WHISPER_MODEL_SIZE` | `base` | 模型大小：`tiny` / `base` / `small` / `medium` / `large` |
| `WHISPER_DEVICE` | `cpu` | 推理设备：`cpu` / `cuda` |
| `WHISPER_COMPUTE_TYPE` | `int8` | 计算类型：`int8` / `float16` / `float32` |

---

## 视频处理配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `FFMPEG_PATH` | `/usr/bin/ffmpeg` | FFmpeg 路径（自动查找：env var → config → PATH → imageio_ffmpeg） |
| `TEMP_DIR` | `/tmp/video_optimizer` | 临时文件目录 |
| `MAX_VIDEO_SIZE_MB` | `500` | 上传视频大小限制（MB） |
| `ALLOWED_EXTENSIONS` | `mp4,mov,avi,mkv` | 允许的视频格式（逗号分隔） |

---

## Redis 配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `REDIS_HOST` | `localhost` | Redis 主机 |
| `REDIS_PORT` | `6379` | Redis 端口 |
| `REDIS_DB` | `0` | Redis 数据库编号 |
| `REDIS_PASSWORD` | `null` | Redis 密码（可选） |

> Redis 不可达时，任务存储自动降级到内存模式（TTL=1h，最多 10,000 条）。

---

## 存储配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `STORAGE_TYPE` | `local` | 存储类型：`local` |
| `LOCAL_STORAGE_PATH` | `./storage` | 本地存储路径 |

---

## 平台配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEFAULT_PLATFORM` | `douyin` | 默认目标平台 |
| `ENABLE_CROSS_PLATFORM` | `true` | 是否启用跨平台适配 |

---

## API 配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `API_HOST` | `0.0.0.0` | API 监听地址 |
| `API_PORT` | `8080` | API 端口 |
| `API_DEBUG` | `false` | 调试模式 |
| `CORS_ORIGINS` | `["*"]` | CORS 允许来源（逗号分隔） |

---

## 功能开关

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ENABLE_AUDIO_TRANSCRIPTION` | `true` | 启用 Whisper 音频转录 |
| `ENABLE_VISUAL_ANALYSIS` | `true` | 启用视频帧分析 |
| `ENABLE_LLM_OPTIMIZATION` | `true` | 启用 LLM 优化 |
| `ENABLE_PLATFORM_ADAPTATION` | `true` | 启用平台适配 |
| `ENABLE_BATCH_PROCESSING` | `true` | 启用批量处理 |
| `ENABLE_A_B_TESTING` | `false` | 启用 A/B 测试（实验性） |

---

## 最小配置示例

```bash
# .env 最小配置（edge TTS 免费，无需其他 Key）
LLM_API_KEY=sk-xxx           # DeepSeek API Key（必须）
```

## 完整配置示例

```bash
# LLM
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-xxx
LLM_MODEL=claude-sonnet-4-6

# TTS
TTS_VOICE_NAME=siliconflow:anna
SILICONFLOW_API_KEY=sk-xxx
TTS_VOICE_RATE=5
TTS_VOICE_VOLUME=1.2

# 字幕
SUBTITLE_ENABLED=true
SUBTITLE_FONT_SIZE=40
SUBTITLE_FONT_COLOR=yellow

# 发布
UPLOAD_POST_ENABLED=true
UPLOAD_POST_API_KEY=xxx
UPLOAD_POST_USERNAME=myuser
UPLOAD_POST_PLATFORMS=tiktok,youtube

# 系统
FFMPEG_PATH=/usr/local/bin/ffmpeg
TEMP_DIR=/data/tmp
WHISPER_MODEL_SIZE=small
REDIS_HOST=redis-server
```
