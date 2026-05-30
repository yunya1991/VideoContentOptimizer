# Video AI Optimizer - 视频智能优化工具

![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

面向中国短视频创作者的 AI 驱动视频优化平台 🎬

---

## ✨ 核心功能

- 📊 **智能视频分析** - 自动识别视频意图、提取关键词、评估质量
- 🧠 **AI 文案优化** - 基于 LLM 的文案重写、标题生成
- 🎬 **批量处理** - 支持批量视频分析与优化
- 💡 **创意增强** - 多版本生成、A/B 测试
- 📱 **平台适配** - 抖音/小红书/微信格式自适应
- 🔄 **流程闭环** - 从分析→优化→重生成→发布

---

## 🏗️ 技术架构

```
┌─────────────────────────────────────────┐
│           Streamlit Web UI (端口 8501)          │
│  视频上传 | 分析结果 | 优化建议 | 对比预览      │
└──────────────────────┬──────────────────────────┘
                       ↓
┌─────────────────────────────────────────┐
│        FastAPI Backend (端口 8080)             │
│  /api/v2/analyzer | /api/v2/optimizer | ...  │
└──────────────────────┬──────────────────────────┘
                       ↓
┌─────────────────────────────────────────┐
│             核心服务层                           │
│  ┌──────────────┬──────────────┬──────────┐  │
│  │ 视频分析引擎  │ 智能优化引擎  │ 重生成  │  │
│  │ (Whisper+CV) │ (LLM驱动)    │ (FFmpeg) │  │
│  └──────────────┴──────────────┴──────────┘  │
└───────────────────┘
```

---

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/VideoContentOptimizer.git
cd VideoContentOptimizer
```

### 2. 创建虚拟环境（推荐）

```bash
python -m venv venv

# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，至少配置：
- `LLM_API_KEY`: 大模型的 API Key (DeepSeek/OpenAI/Claude)
- `LLM_PROVIDER`: 选择提供商 (deepseek/openai/anthropic)

### 5. 安装系统依赖

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y ffmpeg

# macOS
brew install ffmpeg

# 验证安装
ffmpeg -version
```

### 6. 运行服务

#### 启动 API 服务：

```bash
cd VideoContentOptimizer
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

访问 API 文档：http://localhost:8080/docs

#### 启动 Web UI：

```bash
streamlit run webui/main.py --server.port 8501
```

访问 Web UI：http://localhost:8501

---

## 📖 使用指南

### 基础流程

1. **上传视频** - 在 Web UI 上传视频文件 (支持 mp4, mov, avi, mkv)
2. **自动分析** - 系统自动提取元数据、转录音频、识别意图
3. **查看建议** - 获取质量评分、关键词、改进建议
4. **优化内容** - 生成优化文案、多个标题版本
5. **对比选择** - 对比原版和优化版，选择最佳方案
6. **发布分享** - 导出或发布到各平台

### API 使用示例

#### 分析视频

```bash
curl -X POST "http://localhost:8080/api/v2/analyze" \
  -H "Content-Type: multipart/form-data" \
  -F "video=@sample.mp4"
```

#### 优化文案

```bash
curl -X POST "http://localhost:8080/api/v2/optimizer/optimize" \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_id": "task_12345",
    "optimization_types": ["script", "title"],
    "num_variants": 3
  }'
```

---

## 🧪 运行测试

```bash
# 运行所有测试
pytest test/ -v

# 运行特定测试
pytest test/services/test_analyzer.py -v

# 生成覆盖率报告
pytest --cov=app --cov-report=html
```

---

## 📂 项目结构

```
VideoContentOptimizer/
├── app/
│   ├── main.py                       # FastAPI 主应用
│   ├── config.py                     # 配置管理
│   ├── services/                     # 核心服务层
│   │   ├── analyzer/                # 视频分析模块
│   │   ├── optimizer/               # 优化建议模块
│   │   └── regenerator/             # 重生成模块
│   ├── controllers/                 # API 控制器
│   │   ├── v2/                     # v2 API
│   │   └── v1/                     # v1 API (兼容)
│   ├── models/                      # 数据模型
│   └── utils/                       # 工具函数
├── webui/                           # Streamlit 前端
│   ├── main.py                     # Web UI 主入口
│   ├── pages/                      # 页面
│   └── components/                 # UI 组件
├── resource/                        # 资源文件
│   ├── prompts/                   # Prompt 库
│   └── templates/                 # 平台模板
├── test/                            # 测试文件
├── docker-compose.yml               # Docker Compose 配置
├── requirements.txt                 # Python 依赖
├── .env.example                    # 环境变量示例
├── .gitignore                      # Git 忽略文件
└── README.md                       # 本文件
```

---

## ⚙️ 配置说明

### LLM 配置

支持以下 LLM 提供商：
- **DeepSeek** (推荐，性价比高)
- **OpenAI** (GPT-3.5/GPT-4)
- **Anthropic** (Claude)
- **自定义 OpenAI 兼容接口**

在 `.env` 中配置：
```bash
LLM_PROVIDER=deepseek
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://api.deepseek.com/v1  # 可选
LLM_MODEL=deepseek-chat
```

### 平台配置

在 `resource/templates/` 中配置各平台：
- `douyin_template.json` - 抖音配置
- `xiaohongshu_template.json` - 小红书配置
- `weixin_template.json` - 微信视频号配置

---

## 🎯 路线图

- [x] 视频元数据提取
- [x] 音频转录 (Whisper)
- [x] 视频意图识别 (LLM)
- [x] 文案优化 (LLM)
- [x] 标题生成 (LLM)
- [x] 平台适配建议
- [ ] 视频重生成 (FFmpeg)
- [ ] 批量处理优化
- [ ] A/B 测试功能
- [ ] 平台 API 集成
- [ ] 数据统计分析
- [ ] 移动端适配

---

## 🤝 贡献指南

欢迎贡献！请遵循以下步骤：

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代、快速的 Web 框架
- [Streamlit](https://streamlit.io/) - 快速构建数据应用
- [Faster Whisper](https://github.com/guillaumekln/faster-whisper) - 快速音频转录
- [OpenCV](https://opencv.org/) - 计算机视觉库
- [FFmpeg](https://ffmpeg.org/) - 视频处理工具

---

## 📧 联系方式

- 项目主页：[GitHub Repository](https://github.com/yourusername/VideoContentOptimizer)
- 问题反馈：[Issues](https://github.com/yourusername/VideoContentOptimizer/issues)
- 讨论区：[Discussions](https://github.com/yourusername/VideoContentOptimizer/discussions)

---

⭐ **如果这个项目对你有帮助，请给它一个星标！**

---

## 📸 **演示截图 (ASCII 艺术版)**

> 由于服务器无图形界面，以下使用 ASCII 艺术展示界面效果。

### **1. 视频分析页面**
```
┌─────────────────────────────────────┐
│ 🎬 Video AI Optimizer            │
│ 智能视频分析与优化平台 - 专为一人公司设计 │
├─────────────────────────────────────┤
│ [📊 视频分析] [🧠 智能优化] [🎬 重生成] │
├─────────────────────────────────────┤
│ 上传视频: [浏览文件...]           │
│ ✓ sample_video.mp4 (5.0s, 640x480) │
│                                     │
│ [视频预览窗口 - 显示第一帧图像]        │
│                                     │
│ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐│
│ │⏱️ 5.0s│ │640x480│ │24FPS │ │mp4  ││
│ └──────┘ └──────┘ └──────┘ └──────┘│
│                                     │
│ 📝 音频转录: 这是一段测试转录文本...   │
│ 🎯 视频意图: 教育 | 编程教学 | 励志 │
│ ⭐ 质量评分: 内容8.5 制作7.2 互动8.8 │
└─────────────────────────────────────┘
```

### **2. 智能优化页面**
```
┌─────────────────────────────────────┐
│ 🧠 智能优化                        │
│ 基于 LLM 的文案优化、标题生成、平台适配 │
├─────────────────────────────────────┤
│ ⚙️ 优化选项:                      │
│ ☑️ 文案优化  ☑️ 标题生成  ☑️ 平台适配│
│ 目标平台: [抖音 ▼]  标题变体: [5 ▼]│
│                                     │
│ [🚀 开始优化] (蓝色大按钮)          │
│                                     │
│ ✍️ 文案优化:                       │
│ ┌─────────────────┐┌─────────────────┐│
│ │原文案:          ││优化后:          ││
│ │如何在30天内    ││他用30天从0学会  ││
│ │学会编程        ││编程，年薪涨20万！││
│ └─────────────────┘└─────────────────┘│
│ 📝 标题生成: 他用30天从0学会编程...   │
│ 📱 平台适配: 抖音竖屏 + 快节奏...   │
│ 🎉 优化完成！预计播放量提升 150%+   │
└─────────────────────────────────────┘
```

### **3. API 文档页面 (Swagger UI)**
```
┌─────────────────────────────────────┐
│ Swagger UI - Video AI Optimizer API │
│ http://localhost:8080/docs           │
├─────────────────────────────────────┤
│ [GET] /           API 根路径         │
│ [GET] /health      健康检查          │
│ [POST] /api/v2/analyze       分析视频│
│ [POST] /api/v2/batch/analyze 批量分析│
│                                     │
│ ▼ POST /api/v2/analyze              │
│   Parameters:                       │
│   - video: [选择文件] sample.mp4   │
│   - extract_keywords: true           │
│   - predict_trend: true             │
│   [Execute]                         │
│   Responses: Code: 200 - 分析成功   │
└─────────────────────────────────────┘
```

