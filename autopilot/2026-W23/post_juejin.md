# 我是如何用 FastAPI + Whisper 做了个视频优化工具

最近做了一个叫 **VideoContentOptimizer** 的开源项目，专门面向中国短视频创作者，帮他们用 AI 分析视频、优化文案、甚至批量处理。今天聊聊技术实现和一些踩坑的点。

## 整体架构：Streamlit 前台 + FastAPI 后台

```
Streamlit (8501) → FastAPI (8080) → 核心服务层
```

前台用 Streamlit 做交互，好处是快速出原型，支持文件上传、表单配置、结果展示。后台用 FastAPI 提供 RESTful API，核心服务层拆了三个引擎：视频分析引擎（Whisper+CV）、智能优化引擎（LLM 驱动）、重生成引擎（FFmpeg）。

## 技术难点一：LLM 调用与进化引擎

项目里最核心的是“智能优化引擎”。用户上传视频后，系统会：

1. **用 Whisper 转录音频**，提取字幕文本
2. **调用 LLM** 分析视频意图、提取关键词、评估质量
3. **生成 3 张优化方向卡片**，用户选择后进入参数表单

这里有个设计亮点：**自主进化引擎**。每次用户选择优化方向，系统会把这次选择记录下来，作为“Soul 用户画像”的进化材料。具体实现是维护一个 JSON 文件，记录每个用户的偏好历史，下次调用 LLM 时，把历史作为上下文传入 prompt。

```python
# 进化引擎核心逻辑
def evolve_soul(user_id: str, choice: dict):
    profile = load_profile(user_id)
    profile["history"].append(choice)
    # 用历史数据更新 prompt 模板
    profile["prompt_template"] = update_template(profile["history"])
    save_profile(user_id, profile)
```

这个设计挺有意思——用户用得越多，系统越懂你。但实现时有个坑：**历史数据膨胀问题**。如果用户用了 100 次，prompt 上下文可能超 token 限制。解决方案是只保留最近 10 条记录，加上一个聚合统计字段。

## 技术难点二：TTS 多引擎支持

项目支持 TTS（文字转语音），但不同平台（抖音、小红书、微信）对音频格式要求不同。我实现了多引擎切换：

- **Edge TTS**：免费，音质好，但依赖网络
- **Coqui TTS**：本地运行，但模型大（500MB+）

踩坑点：Coqui TTS 的版本依赖很坑，需要固定 `TTS==0.22.0` 和 `tensorflow==2.13.0`，否则会报 `__import__` 动态导入错误。后来用 `pip freeze` 锁了版本才解决。

## 技术难点三：询问/执行双模式

这个功能是用户反馈驱动的。单视频处理时，用户希望有交互（询问模式），一步步确认参数；批量处理时，用户希望直接跑（执行模式），用默认值。

实现方案：

```python
@app.post("/api/v2/analyzer")
async def analyze_video(
    mode: str = Query("inquiry"),  # inquiry / execution
    video: UploadFile = File(...),
    params: Optional[dict] = Body(None)
):
    if mode == "inquiry":
        return {"step": 1, "suggestions": generate_suggestions(video)}
    elif mode == "execution":
        default_params = load_defaults()
        return {"step": "done", "result": process_video(video, default_params)}
```

## 项目地址

完整代码在 GitHub：[VideoContentOptimizer](https://github.com/your-repo/video-content-optimizer)（请替换为实际链接）

## 求 Star 🌟

如果你觉得这个项目对你有帮助，或者对 AI+视频处理感兴趣，欢迎去 GitHub 点个 Star。目前项目还在迭代中，后续计划加入更多 LLM 模型支持、更智能的进化引擎算法。Star 越多，更新越快 😄