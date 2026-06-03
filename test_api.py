"""
测试 VideoContentOptimizer API
"""

import requests
import json
import sys
import os

API_BASE = "http://localhost:8080"

def test_root():
    """测试根路径"""
    print("\n📍 测试 1: API 根路径")
    print("-" * 60)
    
    response = requests.get(f"{API_BASE}/")
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 成功!")
        print(f"   名称: {data.get('name')}")
        print(f"   版本: {data.get('version')}")
        print(f"   状态: {data.get('status')}")
        return True
    else:
        print(f"❌ 失败: {response.text}")
        return False

def test_health():
    """测试健康检查"""
    print("\n💚 测试 2: 健康检查")
    print("-" * 60)
    
    response = requests.get(f"{API_BASE}/health")
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 成功!")
        print(f"   状态: {data.get('status')}")
        return True
    else:
        print(f"❌ 失败: {response.text}")
        return False

def test_analyze_video(video_path):
    """测试视频分析"""
    print("\n📊 测试 3: 视频分析")
    print("-" * 60)
    
    if not os.path.exists(video_path):
        print(f"❌ 视频文件不存在: {video_path}")
        return False
    
    print(f"上传视频: {video_path}")
    
    with open(video_path, 'rb') as f:
        files = {'video': (os.path.basename(video_path), f, 'video/mp4')}
        data = {'extract_keywords': 'true', 'predict_trend': 'true'}
        
        response = requests.post(f"{API_BASE}/api/v2/analyze", files=files, data=data)
    
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 分析成功!")
        print(f"   状态: {result.get('status')}")
        print(f"   文件名: {result.get('filename')}")
        
        metadata = result.get('metadata', {})
        print(f"   时长: {metadata.get('duration')} 秒")
        print(f"   分辨率: {metadata.get('resolution')}")
        print(f"   帧率: {metadata.get('fps')} FPS")
        print(f"   格式: {metadata.get('format')}")
        
        if result.get('transcript'):
            print(f"   转录: {result['transcript'][:100]}...")
        else:
            print(f"   ⚠️ 转录: null (需要安装 faster-whisper 和 ffmpeg)")
        
        return True
    else:
        print(f"❌ 失败: {response.text}")
        return False

def test_batch_analyze(video_path, num_copies=2):
    """测试批量分析"""
    print("\n📈 测试 4: 批量分析")
    print("-" * 60)
    
    if not os.path.exists(video_path):
        print(f"❌ 视频文件不存在: {video_path}")
        return False
    
    print(f"批量上传 {num_copies} 个视频...")
    
    files = []
    for i in range(num_copies):
        files.append(('videos', (f"video_{i}.mp4", open(video_path, 'rb'), 'video/mp4')))
    
    try:
        response = requests.post(
            f"{API_BASE}/api/v2/batch/analyze",
            files=files,
            data={'parallel_workers': 2}
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 批量分析成功!")
            print(f"   任务ID: {result.get('batch_id')}")
            print(f"   总数: {result.get('total')}")
            print(f"   已处理: {result.get('processed')}")
            return True
        else:
            print(f"❌ 失败: {response.text}")
            return False
    finally:
        for _, (_, f, _) in files:
            f.close()

def test_openapi():
    """测试 OpenAPI 文档"""
    print("\n📖 测试 5: OpenAPI 文档")
    print("-" * 60)
    
    response = requests.get(f"{API_BASE}/openapi.json")
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 文档获取成功!")
        print(f"   标题: {data.get('info', {}).get('title')}")
        print(f"   版本: {data.get('info', {}).get('version')}")
        
        paths = data.get('paths', {})
        print(f"   端点数量: {len(paths)}")
        print(f"   端点列表:")
        for path, methods in paths.items():
            for method in methods.keys():
                print(f"      {method.upper():>6} {path}")
        
        return True
    else:
        print(f"❌ 失败: {response.text}")
        return False

def main():
    """主测试函数"""
    print("🎬 VideoContentOptimizer API 测试")
    print("=" * 60)
    
    # 检查 API 是否运行
    try:
        requests.get(f"{API_BASE}/health", timeout=2)
    except requests.exceptions.ConnectionError:
        print("\n❌ API 服务未运行！")
        print("   请先启动 API 服务:")
        print("   cd /home/ubuntu/VideoContentOptimizer")
        print("   source venv/bin/activate")
        print("   uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload")
        return
    
    # 视频路径
    video_path = "/home/ubuntu/VideoContentOptimizer/test_resources/sample_video.mp4"
    
    # 执行测试
    results = []
    results.append(("API 根路径", test_root()))
    results.append(("健康检查", test_health()))
    results.append(("视频分析", test_analyze_video(video_path)))
    results.append(("批量分析", test_batch_analyze(video_path)))
    results.append(("OpenAPI 文档", test_openapi()))
    
    # 总结
    print("\n" + "=" * 60)
    print("🎉 测试完成！")
    print("=" * 60)
    
    print("\n📊 测试结果:")
    passed = 0
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {status} - {name}")
        if result:
            passed += 1
    
    print(f"\n   总计: {passed}/{len(results)} 通过 ({passed/len(results)*100:.0f}%)")

if __name__ == "__main__":
    main()
