# API 参考文档

基础 URL：`http://localhost:8080`

交互式文档：`http://localhost:8080/docs`（Swagger UI）

---

## 视频分析接口 `/api/v2/analyzer`

### POST /api/v2/analyzer/analyze

上传视频并启动分析任务（异步）。

**请求（multipart/form-data）：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | 视频文件 | 是 | mp4/mov/avi/mkv，最大 500MB |
| `intent_category` | string | 否 | 视频类别（教程/娱乐/通用等） |
| `target_platform` | string | 否 | 目标平台（默认 `douyin`） |

**响应：**
```json
{
  "task_id": "analysis_abc123",
  "status": "processing",
  "message": "分析任务已启动"
}
```

---

### GET /api/v2/analyzer/result/{task_id}

查询分析结果。

**响应：**
```json
{
  "task_id": "analysis_abc123",
  "status": "completed",
  "result": {
    "video_metadata": {
      "duration": 60.5,
      "resolution": "1920x1080",
      "fps": 30.0,
      "format": "mp4"
    },
    "transcript": "视频文字内容...",
    "intent": {
      "category": "教育",
      "sub_category": "编程教学",
      "target_audience": "初学者",
      "emotion": "正向"
    },
    "quality_score": {
      "content_quality": 8.5,
      "production_quality": 7.2,
      "engagement_potential": 8.8,
      "originality": 9.0,
      "overall": 8.4
    }
  }
}
```

---

### POST /api/v2/analyzer/batch

批量分析（多个视频文件）。

**响应：**
```json
{
  "batch_id": "batch_xxx",
  "total": 5,
  "status": "processing"
}
```

---

## 智能优化接口 `/api/v2/optimizer`

### POST /api/v2/optimizer/optimize

综合优化（文案 + 标题 + 平台适配）。

**请求（JSON）：**
```json
{
  "transcript": "原始视频文案内容",
  "keywords": ["AI", "视频", "优化"],
  "intent": {
    "category": "教育",
    "sub_category": "编程",
    "target_audience": "程序员",
    "emotion": "激励"
  },
  "optimization_types": ["script", "title"],
  "num_variants": 3,
  "target_platform": "douyin"
}
```

**响应：**
```json
{
  "optimization_id": "opt_abc123",
  "status": "completed",
  "script_result": {
    "original_script": "原始文案",
    "optimized_script": "优化后文案，增加钩子...",
    "optimization_reasons": ["增强 Hook", "情绪共鸣", "CTA 优化"]
  },
  "title_variants": [
    {
      "title": "你不知道的 AI 秘密，99% 的人都在用错",
      "style": "curiosity_gap",
      "estimated_ctr": 0.082,
      "rationale": "利用信息差刺激点击",
      "target_platform": "douyin"
    }
  ]
}
```

---

### POST /api/v2/optimizer/optimize-script

仅优化文案。

**请求（JSON）：**
```json
{
  "transcript": "原始文案",
  "target_platform": "douyin"
}
```

---

### POST /api/v2/optimizer/generate-titles

生成多个标题变体（8 种风格）。

**请求（JSON）：**
```json
{
  "transcript": "视频内容",
  "keywords": ["Python", "效率"],
  "num_titles": 5,
  "target_platform": "xiaohongshu"
}
```

**响应（数组）：**
```json
[
  {"title": "...", "style": "emotional", "estimated_ctr": 0.075, "rationale": "..."},
  {"title": "...", "style": "number_list", "estimated_ctr": 0.068, "rationale": "..."}
]
```

---

### GET /api/v2/optimizer/supported-types

获取支持的优化类型。

**响应：**
```json
{
  "types": [
    {"id": "script", "name": "文案优化", "description": "优化视频文案，提升吸引力"},
    {"id": "title",  "name": "标题生成", "description": "生成多风格标题变体"}
  ]
}
```

---

## 视频重生成接口 `/api/v2/regenerator`

### POST /api/v2/regenerator/regenerate

基于优化方案重新生成视频（TTS + FFmpeg 合成 + 字幕可选）。

**请求（JSON）：**
```json
{
  "original_video_path": "/path/to/video.mp4",
  "optimization_plan_id": "opt_abc123",
  "variant_id": "v1",
  "target_platforms": ["douyin", "xiaohongshu"]
}
```

**响应：**
```json
{
  "task_id": "regen_abc123",
  "status": "partial",
  "message": "视频重生成已完成"
}
```

---

### GET /api/v2/regenerator/status/{task_id}

查询重生成任务状态。

**响应：**
```json
{
  "task_id": "regen_abc123",
  "status": "partial",
  "progress": 30
}
```

---

### POST /api/v2/regenerator/publish

发布视频到跨平台（通过 upload-post.com）。

**前置条件：** `.env` 中设置 `UPLOAD_POST_ENABLED=true` 和 `UPLOAD_POST_API_KEY`。

**请求（Query 参数 + JSON Body）：**

| Query 参数 | 类型 | 说明 |
|---|---|---|
| `platform` | string | 默认平台（当 metadata 不含 platforms 时使用） |

```json
{
  "video_path": "/path/to/video.mp4",
  "title": "视频标题",
  "platforms": ["douyin", "youtube"]
}
```

**响应（成功）：**
```json
{
  "request_id": "upload_abc123",
  "platforms": ["tiktok", "youtube"],
  "skipped": [],
  "response": {"status": "queued"}
}
```

**错误码：**
| 状态码 | 原因 |
|--------|------|
| 400 | 所有平台均不支持，或 API Key 未配置 |
| 404 | 视频文件不存在 |
| 503 | `UPLOAD_POST_ENABLED=false`（提示配置方法） |
| 502 | upload-post.com API 返回错误 |

---

### GET /api/v2/regenerator/features

获取重生成模块各功能状态。

**响应：**
```json
{
  "features": [
    {"name": "平台分辨率转换", "status": "available"},
    {"name": "TTS 音频生成",  "status": "available"},
    {"name": "音视频合成",    "status": "available"},
    {"name": "字幕烧录",      "status": "available"},
    {"name": "跨平台发布",    "status": "available"},
    {"name": "版本对比",      "status": "planned"}
  ]
}
```

---

## 全局接口

### GET /health

健康检查。

**响应：**
```json
{
  "status": "ok",
  "version": "2.0.0"
}
```

### GET /api/v2/

API 版本信息。

---

## Python SDK 示例

```python
from app.utils.ai_client import LLMClient
from app.services.tts.tts_service import tts
from app.services.subtitle.sub_maker import SubMaker
from app.services.publish.upload_post_client import PublishManager

# LLM 调用（自动从 settings 读取配置）
client = LLMClient.from_settings()
result = client.generate("优化这段文案：...", system_prompt="你是视频文案专家")
json_result = client.generate_json("生成5个标题，返回 JSON 数组")

# TTS 生成
ok = tts(
    text="你好，欢迎观看本视频",
    voice_name="edge:zh-CN-XiaoxiaoNeural",
    output_file="/tmp/audio.mp3",
    voice_rate=0,
    voice_volume=1.0,
)

# 字幕生成（按比例分配）
maker = SubMaker.from_timed_text("第一句话。第二句话。第三句话", audio_duration_seconds=9.0)
maker.save_srt("/tmp/subtitle.srt")
print(maker.to_srt())

# 发布到多平台
pm = PublishManager.from_settings()
result = pm.publish(
    video_path="/tmp/video.mp4",
    title="我的视频",
    platforms=["douyin", "youtube"],
)
print(result["request_id"])
```
