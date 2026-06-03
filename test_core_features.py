"""
测试 VideoContentOptimizer 核心功能
"""

import sys
import os

# 添加项目路径
project_root = "/home/ubuntu/VideoContentOptimizer"
sys.path.append(project_root)

print("🎬 VideoContentOptimizer 功能测试")
print("=" * 60)

# ==================== 测试 1: 视频解析 ====================
print("\n📊 测试 1: 视频元数据解析")
print("-" * 60)

try:
    from app.services.analyzer.video_parser import VideoParser
    
    parser = VideoParser()
    test_video = os.path.join(project_root, "test_resources", "sample_video.mp4")
    
    if os.path.exists(test_video):
        metadata = parser.parse_video(test_video)
        
        print(f"✅ 视频解析成功！")
        print(f"   - 时长: {metadata.duration:.2f} 秒")
        print(f"   - 分辨率: {metadata.resolution}")
        print(f"   - 帧率: {metadata.fps} FPS")
        print(f"   - 格式: {metadata.format}")
        print(f"   - 比特率: {metadata.bitrate} bps")
    else:
        print(f"❌ 测试视频不存在: {test_video}")
except Exception as e:
    print(f"❌ 视频解析失败: {e}")
    import traceback
    traceback.print_exc()

# ==================== 测试 2: LLM 客户端 ====================
print("\n🧠 测试 2: LLM 客户端")
print("-" * 60)

try:
    from app.utils.ai_client import LLMClient
    
    # 使用模拟模式（无 API Key）
    client = LLMClient(provider="deepseek", api_key="test_key", base_url="https://api.deepseek.com/v1")
    
    print(f"✅ LLM 客户端初始化成功")
    print(f"   - Provider: {client.provider}")
    print(f"   - Model: {client.model}")
    print(f"   - Base URL: {client.base_url}")
except Exception as e:
    print(f"❌ LLM 客户端初始化失败: {e}")

# ==================== 测试 3: 数据模型 ====================
print("\n📦 测试 3: 数据模型 (Pydantic)")
print("-" * 60)

try:
    from app.models.schema import VideoMetadata, VideoIntent, QualityScore
    from datetime import datetime
    
    # 创建测试数据
    metadata = VideoMetadata(
        duration=45.5,
        resolution="1920x1080",
        fps=30.0,
        bitrate=5000000,
        format="mp4",
        codec="h264"
    )
    
    intent = VideoIntent(
        category="教育",
        sub_category="编程教学",
        target_audience="初学者",
        emotion="励志",
        confidence=0.85,
        core_message="30天学会编程"
    )
    
    quality_score = QualityScore(
        content_quality=8.5,
        production_quality=7.0,
        engagement_potential=9.0,
        originality=7.5,
        overall_score=8.0,
        improvement_areas=["增加案例", "优化节奏"],
        recommendation="内容质量高，建议增加互动环节"
    )
    
    print("✅ 数据模型创建成功")
    print(f"   - VideoMetadata: {metadata.resolution}, {metadata.duration}s")
    print(f"   - VideoIntent: {intent.category} - {intent.sub_category}")
    print(f"   - QualityScore: 综合 {quality_score.overall_score}/10")
except Exception as e:
    print(f"❌ 数据模型测试失败: {e}")
    import traceback
    traceback.print_exc()

# ==================== 测试 4: 配置管理 ====================
print("\n⚙️ 测试 4: 配置管理")
print("-" * 60)

try:
    from app.config import get_settings
    
    settings = get_settings()
    
    print("✅ 配置加载成功")
    print(f"   - LLM Provider: {settings.LLM_PROVIDER}")
    print(f"   - API Port: {settings.API_PORT}")
    print(f"   - Max Video Size: {settings.MAX_VIDEO_SIZE_MB} MB")
    print(f"   - Max Batch Videos: {settings.MAX_BATCH_VIDEOS}")
except Exception as e:
    print(f"❌ 配置加载失败: {e}")
    import traceback
    traceback.print_exc()

# ==================== 测试 5: FastAPI 应用 ====================
print("\n🚀 测试 5: FastAPI 应用")
print("-" * 60)

try:
    from app.main import app
    
    print("✅ FastAPI 应用创建成功")
    print(f"   - 应用标题: {app.title}")
    print(f"   - 版本: {app.version}")
    print(f"   - 路由数量: {len(app.routes)}")
    
    # 列出路由
    print("\n   路由列表:")
    for route in app.routes:
        if hasattr(route, 'path'):
            methods = getattr(route, 'methods', set())
            print(f"      {list(methods) if methods else 'N/A'} {route.path}")
except Exception as e:
    print(f"❌ FastAPI 应用测试失败: {e}")
    import traceback
    traceback.print_exc()

# ==================== 测试总结 ====================
print("\n" + "=" * 60)
print("🎉 测试完成！")
print("=" * 60)

print("\n💡 提示:")
print("   1. 访问 Web UI: http://localhost:8501")
print("   2. 访问 API 文档: http://localhost:8080/docs")
print("   3. 测试视频位置: test_resources/sample_video.mp4")
print("   4. 查看项目总结: PROJECT_SUMMARY.md")
