"""
浏览器自动化上传 - 快速使用示例

前置条件:
1. 已部署 tencent-novnc-chromium-cdp Skill（远程浏览器）
2. 浏览器监听 127.0.0.1:9223
3. 已在浏览器中登录目标平台（抖音/小红书等）

运行:
    pip install websocket-client
    python examples/browser_upload_demo.py
"""

import sys
import os

# 添加项目根目录到 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.browser_upload.manager import BrowserUploadManager
from app.services.browser_upload.cdp_client import is_cdp_available


def demo_health_check():
    """步骤1: 健康检查"""
    print("=" * 60)
    print("【步骤1】检查 CDP 浏览器是否可用")
    print("=" * 60)

    if not is_cdp_available():
        print("❌ CDP 浏览器不可用")
        print("   请先部署 tencent-novnc-chromium-cdp Skill")
        print("   并确保 127.0.0.1:9223 可访问")
        return False

    print("✅ CDP 浏览器可用")
    mgr = BrowserUploadManager()
    info = mgr.health_check()
    print(f"   CDP URL: {info['cdp_url']}")
    print(f"   支持平台: {', '.join(info['supported_platforms'])}")
    return True


def demo_list_platforms():
    """步骤2: 列出支持的平台"""
    print()
    print("=" * 60)
    print("【步骤2】支持的上传平台")
    print("=" * 60)

    mgr = BrowserUploadManager()
    platforms = mgr.list_platforms()
    for p in platforms:
        print(f"   [{p['platform_id']:12s}] {p['display_name']}")
        print(f"               -> {p['upload_url']}")


def demo_upload_video(video_path: str, title: str, platforms: list):
    """步骤3: 上传视频到多个平台"""
    print()
    print("=" * 60)
    print(f"【步骤3】上传视频: {os.path.basename(video_path)}")
    print(f"         标题: {title}")
    print(f"         平台: {', '.join(platforms)}")
    print("=" * 60)

    if not os.path.isfile(video_path):
        print(f"❌ 视频文件不存在: {video_path}")
        print("   请先准备一个测试视频文件")
        return

    mgr = BrowserUploadManager()
    result = mgr.upload_to_platforms(
        video_path=video_path,
        title=title,
        platforms=platforms,
        description="这是一个测试视频",
        tags=["测试", "demo"],
    )

    print(f"\n📊 汇总: 成功 {result['success']}/{result['total']}, 失败 {result['failed']}")
    print()

    for r in result["results"]:
        status_icon = "✅" if r["success"] else "❌"
        print(f"   {status_icon} {r['platform']}")
        print(f"      {r.get('message', '')}")
        if r.get("screenshot"):
            print(f"      截图: {r['screenshot']}")
        details = r.get("details", {})
        if details:
            for k, v in details.items():
                print(f"      {k}: {v}")


def demo_session_check(url: str):
    """步骤4: 检查浏览器是否能访问某 URL"""
    print()
    print("=" * 60)
    print(f"【步骤4】检查浏览器访问: {url}")
    print("=" * 60)

    mgr = BrowserUploadManager()
    result = mgr.check_browser_session(url)
    if result.get("ok"):
        print(f"✅ 访问成功")
        print(f"   当前 URL: {result.get('url')}")
        print(f"   页面标题: {result.get('title')}")
        if result.get("screenshot"):
            print(f"   截图: {result.get('screenshot')}")
    else:
        print(f"❌ 访问失败: {result.get('message')}")


if __name__ == "__main__":
    print("🎬 VideoContentOptimizer + 浏览器自动化上传 Demo")
    print()

    # 1. 健康检查
    ok = demo_health_check()
    if not ok:
        print("\n请先完成远程浏览器部署后再重试")
        sys.exit(1)

    # 2. 列出平台
    demo_list_platforms()

    # 3. 检查抖音创作者平台登录状态
    demo_session_check("https://creator.douyin.com/")

    # 4. 示例上传（取消注释并准备视频文件后运行）
    # demo_upload_video(
    #     video_path="/path/to/your/video.mp4",
    #     title="我的测试视频 - AI 生成",
    #     platforms=["douyin"],
    # )

    print()
    print("=" * 60)
    print("🎉 Demo 完成！若要实际上传，请：")
    print("   1. 在 noVNC 浏览器中登录目标平台")
    print("   2. 取消注释 demo_upload_video() 调用并填入视频路径")
    print("   3. 重新运行此脚本")
    print("=" * 60)
