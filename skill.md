# 视频AI优化器技能文档

## 技能概述

视频AI优化器是一个面向中国短视频创作者的AI驱动视频优化平台，专为"一人公司"设计，提供从视频分析到智能优化、重生成、发布的全流程解决方案。

## 核心功能

### 1. 智能视频分析
- 自动提取视频元数据（时长/分辨率/帧率/比特率）
- AI音频转录（基于Faster Whisper）
- 视频意图识别（LLM驱动）
- 多维度质量评分（内容/制作/互动/原创）

### 2. 智能优化引擎
- 文案优化（Hook + 节奏 + CTA）
- 标题生成（8种风格，5-10个变体）
- 平台自适应（抖音/小红书/微信）
- 关键词提取、热度预测

### 3. 视频重生成
- 基于优化方案重新生成视频
- 多版本生成（A/B测试）
- 平台模板自动适配
- TTS配音（开发中）

### 4. 批量处理
- 批量上传视频（支持50+个）
- 并行处理（线程池加速）
- 进度跟踪、结果汇总
- 一键发布到多平台

## 技术架构

### 后端技术栈
- **FastAPI**：高性能异步API框架
- **Uvicorn**：ASGI服务器
- **SQLAlchemy**：ORM数据库操作
- **Redis**：缓存和消息队列
- **PostgreSQL**：主数据库

### AI服务集成
- **Faster Whisper**：音频转录
- **OpenAI API**：LLM智能分析
- **OpenCV**：视频处理
- **MoviePy**：视频编辑

### 前端技术栈
- **Streamlit**：Web UI框架
- **Streamlit Option Menu**：导航组件
- **Pillow**：图像处理

### 数据处理
- **Pandas**：数据分析
- **NumPy**：数值计算
- **FFmpeg**：视频编解码

## 部署架构

### 开发环境
- **Docker Compose**：容器化部署
- **Python 3.10+**：运行环境
- **虚拟环境**：venv隔离

### 生产环境
- **腾讯云CVM/Lighthouse**：服务器
- **Docker容器**：应用部署
- **Nginx**：反向代理
- **云监控**：性能监控

## 使用流程

### 1. 视频上传
用户通过Streamlit Web界面上传原始视频文件，系统自动进行格式验证。

### 2. 智能分析
FastAPI后端调用AI服务对视频进行全面分析，生成详细分析报告。

### 3. 优化建议
基于分析结果，LLM生成具体的优化建议和修改方案。

### 4. 一键优化
用户确认优化方案后，系统自动执行视频重生成处理。

### 5. 预览确认
优化完成后，用户可以在Web界面预览效果并确认。

### 6. 发布管理
选择目标平台，设置发布时间，一键发布到多平台。

## 配置说明

### 环境变量配置
```bash
# 数据库配置
DATABASE_URL=postgresql://user:password@localhost/video_optimizer
REDIS_URL=redis://localhost:6379

# AI服务配置
OPENAI_API_KEY=your_openai_api_key
WHISPER_MODEL=base

# 应用配置
DEBUG=false
LOG_LEVEL=INFO
UPLOAD_DIR=/data/uploads

# 平台配置
DOUYIN_ACCESS_TOKEN=your_douyin_token
XIAOHONGSHU_ACCESS_TOKEN=your_xhs_token
WECHAT_ACCESS_TOKEN=your_wechat_token
```

### 安装依赖
```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装Python依赖
pip install -r requirements.txt

# 安装FFmpeg
sudo apt update
sudo apt install ffmpeg

# 启动服务
docker-compose up -d
```

## 故障排查

### 常见问题
1. **视频上传失败**：检查文件格式和大小限制，确认FFmpeg安装
2. **AI分析超时**：检查OpenAI API配额和网络连接
3. **数据库连接失败**：检查PostgreSQL服务状态和连接字符串

### 日志查看
```bash
# 查看应用日志
tail -f logs/app.log

# 查看API访问日志
tail -f logs/api.log

# 查看AI服务日志
tail -f logs/ai.log
```

## 性能优化

### 服务器配置建议
- CPU：4核以上（支持并行视频处理）
- 内存：8GB以上（AI模型加载）
- 存储：SSD，至少100GB（视频文件存储）
- 带宽：10Mbps以上（视频上传下载）

### 缓存策略
- Redis缓存热点数据和AI分析结果
- 视频文件分块上传和断点续传
- 数据库连接池优化

## 安全考虑

### 数据安全
- 视频文件加密存储
- API接口JWT认证
- 敏感信息环境变量管理

### 访问控制
- API访问频率限制
- 文件上传类型和大小限制
- 操作日志审计



## 联系方式

- 项目地址：https://github.com/yunya1991/VideoContentOptimizer
- 问题反馈：GitHub Issues
- 技术文档：项目Wiki

---

*最后更新：2026年5月30日*
*技术栈：Python FastAPI + Streamlit + PostgreSQL + Redis*