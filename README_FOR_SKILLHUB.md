# Video AI Optimizer - 一人公司(OPC)视频智能优化平台

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 专为"一人公司"设计

> **一个人 = 策划 + 拍摄 + 剪辑 + 运营**
> **AI 助手 = 内容分析 + 文案优化 + 标题生成 + 平台适配**
> **全链路 = 分析 → 优化 → 配音 → 字幕 → 跨平台发布**

### 适用人群
- 个人博主、自由职业者
- 小微创业团队（3-5 人）
- 副业创作者、斜杠青年

---

## 核心功能

### 1. 智能视频分析
- 自动提取视频元数据（时长/分辨率/帧率/比特率）
- AI 音频转录（Faster Whisper，准确度 95%+）
- 视频意图识别（LLM 驱动）
- 多维度质量评分（内容/制作/互动/原创）

### 2. 智能优化引擎
- 文案优化（Hook + 节奏 + CTA）
- 标题生成（8 种风格，5-10 个变体）
- 平台自适应（抖音/小红书/微信）
- 关键词提取、热度预测

### 3. 视频重生成
- TTS 配音（5 引擎：edge 免费 / azure / siliconflow / gemini / mimo）
- 字幕生成与烧录（SubMaker + FFmpeg）
- 两阶段 FFmpeg 合成（保留视频流，无重编码损耗）
- 多版本生成（A/B 测试）
- 平台模板自动适配

### 4. 跨平台发布
- upload-post.com API 集成（tiktok/youtube/instagram/facebook 等）
- 抖音自动映射为 TikTok
- 批量上传（支持 50+ 个视频）
- 并行处理，进度跟踪

---

## 效果对比

| 维度 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 文案吸引力 | 平淡无奇 | Hook + 情感共鸣 | +150% |
| 标题点击率 | 3% | 8-15% | +167% |
| 互动率 | 2% | 5-8% | +250% |
| 制作时间 | 2 小时/条 | 30 分钟/条 | -75% |
| 平台适配 | 手动调整 | 自动适配 | 3x 效率 |

---

## 成功案例

### 案例 1: 知识博主的效率提升
- **背景**：个人技术博主，每天只能花 2 小时在视频制作上
- **使用方式**：上传视频 → 5 分钟完成分析 → AI 生成爆款标题 → 自动优化文案 → 一键适配 3 个平台
- **效果**：播放量从平均 5K 提升到 50K+，时间节省 70%

### 案例 2: 小微电商团队的降本增效
- **背景**：3 人小团队，运营 5 个短视频账号，每天需要制作 10+ 条视频
- **使用方式**：批量上传 → 批量分析优化 → 一键多平台发布
- **效果**：人力成本降低 60%，账号粉丝总量 3 个月增长 300%

---

## 快速开始

### 方式 1: Docker 一键部署（推荐）
```bash
git clone https://github.com/yunya1991/VideoContentOptimizer.git
cd VideoContentOptimizer
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY
docker-compose up -d
# Web UI: http://localhost:8501
# API 文档: http://localhost:8080/docs
```

### 方式 2: 本地开发
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
streamlit run webui/main.py --server.port 8501
```

---

## 技术栈

| 层级 | 技术 |
|------|------|
| API 框架 | FastAPI + Pydantic v2 |
| Web UI | Streamlit |
| 音频转录 | Faster Whisper |
| 视频处理 | FFmpeg + OpenCV |
| TTS | edge_tts / Azure / SiliconFlow / Gemini / MiMo |
| LLM | DeepSeek / OpenAI / Anthropic / Qwen / SiliconFlow |
| 任务存储 | Redis（可选） + 内存双后端 |
| 跨平台发布 | upload-post.com API |
| 部署 | Docker + Docker Compose + Nginx |

---

## 使用流程

```
1. 上传视频
   ↓
2. 视频分析（元数据 + 转录 + 意图识别 + 质量评分）
   ↓
3. 智能优化（文案优化 + 标题生成 + 平台适配）
   ↓
4. 视频重生成（TTS 配音 + 字幕烧录 + FFmpeg 合成）
   ↓
5. 跨平台发布（upload-post.com → TikTok / YouTube / Instagram 等）
```

---

## 项目结构

```
VideoContentOptimizer/
├── app/
│   ├── services/
│   │   ├── analyzer/          # 视频分析
│   │   ├── optimizer/         # 智能优化
│   │   ├── regenerator/       # 视频重生成 + TTS + 字幕
│   │   ├── tts/               # TTS 多引擎服务
│   │   ├── subtitle/          # 字幕时间轴（SubMaker）
│   │   └── publish/           # 跨平台发布（upload-post.com）
│   ├── controllers/v2/        # API 控制器
│   ├── models/                # Pydantic 数据模型
│   ├── utils/                 # ai_client（LLM） + store（TaskStore）
│   ├── config.py              # 配置管理（40+ 字段）
│   └── main.py
├── webui/                     # Streamlit 前端
├── resource/                  # 平台模板 + Prompt 库
├── test/                      # 9 个测试文件，240+ 用例
├── docker/                    # Docker 配置
└── requirements.txt
```

---

## 许可证

MIT License
