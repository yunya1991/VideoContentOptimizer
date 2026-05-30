---
name: video-ai-optimizer
description: "视频AI优化器技能，用于视频分析、智能优化、重生成和发布管理。触发词：视频优化、AI视频处理、短视频优化、视频重生成、视频分析、智能剪辑、视频发布、批量视频处理、OpenAI视频、Whisper转录"
---

# 视频AI优化器技能

## 快速导航

**用户需求 → 操作流程**

- 🎯 **部署安装** → 环境准备 → Docker部署 → 服务启动
- 📊 **视频分析** → 上传视频 → AI分析 → 查看报告
- 🔧 **智能优化** → 获取建议 → 确认优化 → 重生成视频
- 🚀 **批量处理** → 批量上传 → 并行处理 → 结果汇总
- ⚙️ **配置管理** → 环境配置 → API密钥 → 平台设置
- 🔍 **故障排查** → 日志查看 → 问题诊断 → 解决方案

## AI使用指南

### 场景判断

当用户提到以下关键词时，加载本技能：
- 视频优化、AI视频处理、短视频优化
- 视频重生成、视频分析、智能剪辑
- 视频发布、批量视频处理
- OpenAI视频、Whisper转录

### 操作流程

1. **环境检测**：检查Python、Docker、FFmpeg环境
2. **服务状态**：验证FastAPI和Streamlit服务运行状态
3. **文件操作**：处理视频上传和结果文件
4. **API调用**：调用AI服务进行分析和优化
5. **配置管理**：设置环境变量和平台配置

## 操作流程

### 1. 环境准备和部署

```bash
# 检查系统环境
python --version
docker --version
ffmpeg -version

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# Docker部署
docker-compose up -d
```

### 2. 视频分析流程

```bash
# 启动服务
cd /home/ubuntu/VideoContentOptimizer
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
streamlit run webui/main.py &

# 访问Web界面
# http://服务器IP:8501
```

### 3. 配置管理

```bash
# 环境变量配置
export OPENAI_API_KEY=your_api_key
export DATABASE_URL=postgresql://user:pass@localhost/video_optimizer
export REDIS_URL=redis://localhost:6379

# 平台配置
export DOUYIN_ACCESS_TOKEN=your_token
export XIAOHONGSHU_ACCESS_TOKEN=your_token
```

### 4. 故障排查

```bash
# 查看服务状态
ps aux | grep -E "(uvicorn|streamlit)"

# 查看日志
tail -f logs/app.log
tail -f logs/api.log

# 检查端口占用
netstat -tlnp | grep -E "(8000|8501)"
```

## 交互示例

### 示例1：部署视频优化器

**用户**："帮我部署视频AI优化器"

**执行流程**：
1. 检查系统环境（Python、Docker、FFmpeg）
2. 创建虚拟环境并安装依赖
3. 启动Docker服务
4. 验证服务运行状态
5. 提供访问地址

### 示例2：分析视频内容

**用户**："分析这个视频文件"

**执行流程**：
1. 确认视频文件路径和格式
2. 启动AI分析服务
3. 调用OpenAI API进行内容分析
4. 生成分析报告
5. 提供优化建议

### 示例3：批量处理视频

**用户**："批量优化这些视频文件"

**执行流程**：
1. 确认视频文件目录
2. 启动批量处理模式
3. 监控处理进度
4. 汇总处理结果
5. 提供下载链接

## 故障排查

### 常见问题解决方案

**问题1：服务启动失败**
```bash
# 检查端口占用
sudo lsof -i :8000
sudo lsof -i :8501

# 重启服务
pkill -f uvicorn
pkill -f streamlit
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
streamlit run webui/main.py &
```

**问题2：AI分析超时**
```bash
# 检查OpenAI API配置
echo $OPENAI_API_KEY

# 测试网络连接
curl -I https://api.openai.com

# 调整超时设置
# 在app/main.py中增加timeout参数
```

**问题3：数据库连接失败**
```bash
# 检查PostgreSQL服务
sudo systemctl status postgresql

# 检查连接字符串
echo $DATABASE_URL

# 测试数据库连接
psql $DATABASE_URL -c "SELECT version();"
```

## 性能优化建议

### 服务器配置
- CPU：4核以上支持并行处理
- 内存：8GB以上加载AI模型
- 存储：SSD加速视频读写
- 带宽：10Mbps以上传输视频

### 缓存策略
- Redis缓存热点分析结果
- 视频文件分块处理
- 数据库连接池优化

## 安全考虑

### 数据安全
- 视频文件加密存储
- API接口JWT认证
- 敏感信息环境变量管理

### 访问控制
- API频率限制
- 文件类型和大小限制
- 操作日志审计

---

*技能版本：1.0.0*
*最后更新：2026年5月30日*
*项目地址：https://github.com/yunya1991/VideoContentOptimizer*
