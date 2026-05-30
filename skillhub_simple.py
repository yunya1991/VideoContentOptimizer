#!/usr/bin/env python3
"""
SkillHub 自动上传脚本 - 简化版
"""

from playwright.sync_api import sync_playwright
import time

def main():
    print("🎬 SkillHub 自动上传 - 开始")
    
    with sync_playwright() as p:
        # 启动浏览器（无头模式）
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # 访问 SkillHub
            print("📋 打开 SkillHub 比赛页面...")
            page.goto("https://skillhub.cn/contest", timeout=30000)
            page.wait_for_load_state("load")
            time.sleep(3)
            
            # 截图（调试用）
            page.screenshot(path="/tmp/skillhub_1.png")
            print("✅ 截图: /tmp/skillhub_1.png")
            
            # 尝试点击 "发布参赛 Skill"
            print("📤 尝试点击 '发布参赛 Skill'...")
            
            # 方法 1：通过文本查找
            try:
                page.get_by_text("发布参赛 Skill").first.click(timeout=5000)
                print("✅ 点击成功（方法 1）")
            except:
                # 方法 2：通过按钮查找
                try:
                    page.get_by_role("button", name="发布").click(timeout=5000)
                    print("✅ 点击成功（方法 2）")
                except:
                    print("❌ 未找到按钮，请手动操作")
                    print("页面内容预览:")
                    print(page.content()[:500])
            
            # 等待页面跳转
            time.sleep(3)
            page.screenshot(path="/tmp/skillhub_2.png")
            print("📸 截图: /tmp/skillhub_2.png")
            
            print("\n" + "="*60)
            print("⚠️  自动化暂停")
            print("="*60)
            print("由于 SkillHub 需要登录和复杂交互，")
            print("建议你在本地电脑手动完成上传。")
            print("\n已为你准备好所有材料：")
            print("  - SKILL.md 文件")
            print("  - 填写内容（见 SKILLHUB_UPLOAD_PACK.md）")
            print("  - GitHub URL: https://github.com/yunya1991/VideoContentOptimizer")
            print("="*60)
            
        except Exception as e:
            print(f"❌ 错误: {e}")
            page.screenshot(path="/tmp/skillhub_error.png")
        
        finally:
            browser.close()
            print("🎉 浏览器已关闭")

if __name__ == "__main__":
    main()
