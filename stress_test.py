"""
VideoContentOptimizer - 压力测试 & 多场景模拟
测试目标：
1. API 并发处理能力
2. 大文件上传
3. 批量处理性能
4. 长时间稳定运行
5. 多场景模拟（不同用户行为）
"""

import requests
import time
import concurrent.futures
import os
from pathlib import Path
import json

API_BASE = "http://localhost:8080"
TEST_VIDEO = "/home/ubuntu/VideoContentOptimizer/test_resources/sample_video.mp4"

class StressTest:
    """压力测试类"""
    
    def __init__(self, base_url=API_BASE):
        self.base_url = base_url
        self.results = []
    
    def test_health(self):
        """健康检查测试"""
        print("\n💚 测试 1: 健康检查（100 次连续请求）")
        success = 0
        fail = 0
        start = time.time()
        
        for i in range(100):
            try:
                r = requests.get(f"{self.base_url}/health", timeout=5)
                if r.status_code == 200:
                    success += 1
                else:
                    fail += 1
            except:
                fail += 1
        
        elapsed = time.time() - start
        print(f"   总请求: 100")
        print(f"   成功: {success}")
        print(f"   失败: {fail}")
        print(f"   耗时: {elapsed:.2f}秒")
        print(f"   QPS: {100/elapsed:.2f}")
        return success, fail, elapsed
    
    def test_concurrent_upload(self, num_threads=10):
        """并发上传测试"""
        print(f"\n📤 测试 2: 并发上传（{num_threads} 个线程）")
        
        if not os.path.exists(TEST_VIDEO):
            print(f"   ❌ 测试视频不存在: {TEST_VIDEO}")
            return 0, num_threads, 0
        
        def upload_once(i):
            try:
                with open(TEST_VIDEO, 'rb') as f:
                    files = {'video': ('test.mp4', f, 'video/mp4')}
                    r = requests.post(
                        f"{self.base_url}/api/v2/analyze",
                        files=files,
                        timeout=30
                    )
                    return r.status_code == 200
            except:
                return False
        
        start = time.time()
        success = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(upload_once, i) for i in range(num_threads)]
            for future in concurrent.futures.as_completed(futures):
                if future.result():
                    success += 1
        
        elapsed = time.time() - start
        print(f"   总请求: {num_threads}")
        print(f"   成功: {success}")
        print(f"   失败: {num_threads - success}")
        print(f"   耗时: {elapsed:.2f}秒")
        print(f"   平均响应: {elapsed/num_threads:.2f}秒")
        return success, num_threads - success, elapsed
    
    def test_large_file(self):
        """大文件上传测试（生成 50MB 测试视频）"""
        print("\n📁 测试 3: 大文件上传（50MB）")
        
        # 生成大文件
        large_video = "/tmp/large_test.mp4"
        print(f"   生成 50MB 测试文件...")
        
        try:
            # 使用 dd 生成大文件（用现有视频重复）
            os.system(f"dd if={TEST_VIDEO} of={large_video} bs=1M count=50 2>/dev/null")
            
            if not os.path.exists(large_video):
                print(f"   ❌ 生成大文件失败")
                return 0, 1, 0
            
            start = time.time()
            with open(large_video, 'rb') as f:
                files = {'video': ('large.mp4', f, 'video/mp4')}
                r = requests.post(
                    f"{self.base_url}/api/v2/analyze",
                    files=files,
                    timeout=120
                )
            elapsed = time.time() - start
            
            if r.status_code == 200:
                print(f"   ✅ 成功")
                print(f"   耗时: {elapsed:.2f}秒")
                print(f"   速度: {50/elapsed:.2f} MB/s")
                return 1, 0, elapsed
            else:
                print(f"   ❌ 失败: {r.status_code}")
                return 0, 1, elapsed
        except Exception as e:
            print(f"   ❌ 错误: {e}")
            return 0, 1, 0
        finally:
            if os.path.exists(large_video):
                os.remove(large_video)
    
    def test_batch_performance(self, batch_sizes=[5, 10, 20]):
        """批量处理性能测试"""
        print(f"\n📈 测试 4: 批量处理性能")
        
        if not os.path.exists(TEST_VIDEO):
            print(f"   ❌ 测试视频不存在")
            return
        
        results = []
        for batch_size in batch_sizes:
            print(f"\n   📊 批量大小: {batch_size}")
            
            files = []
            for i in range(batch_size):
                f = open(TEST_VIDEO, 'rb')
                files.append(('videos', ('test.mp4', f, 'video/mp4')))
            
            start = time.time()
            try:
                r = requests.post(
                    f"{self.base_url}/api/v2/batch/analyze",
                    files=files,
                    timeout=300
                )
                elapsed = time.time() - start
                
                if r.status_code == 200:
                    print(f"      ✅ 成功")
                    print(f"      耗时: {elapsed:.2f}秒")
                    print(f"      平均: {elapsed/batch_size:.2f}秒/个")
                    results.append((batch_size, elapsed, True))
                else:
                    print(f"      ❌ 失败: {r.status_code}")
                    results.append((batch_size, elapsed, False))
            except Exception as e:
                print(f"      ❌ 错误: {e}")
                results.append((batch_size, 0, False))
            finally:
                for _, (_, f, _) in files:
                    f.close()
        
        return results
    
    def test_long_running(self, duration_minutes=5):
        """长时间稳定性测试"""
        print(f"\n⏱️ 测试 5: 长时间稳定性（{duration_minutes} 分钟）")
        
        start_time = time.time()
        end_time = start_time + duration_minutes * 60
        count = 0
        success = 0
        
        while time.time() < end_time:
            try:
                r = requests.get(f"{self.base_url}/health", timeout=5)
                if r.status_code == 200:
                    success += 1
                count += 1
            except:
                count += 1
            
            time.sleep(1)  # 每秒一次
        
        print(f"   总请求: {count}")
        print(f"   成功: {success}")
        print(f"   失败: {count - success}")
        print(f"   成功率: {success/count*100:.1f}%")
        return success, count - success
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🧪 VideoContentOptimizer - 压力测试")
        print("=" * 60)
        
        # 检查服务是否运行
        try:
            r = requests.get(f"{self.base_url}/health", timeout=2)
            if r.status_code != 200:
                print("❌ API 服务未运行！")
                print(f"   请先启动: uvicorn app.main:app --host 0.0.0.0 --port 8080")
                return
        except:
            print("❌ API 服务未运行！")
            print(f"   请先启动: uvicorn app.main:app --host 0.0.0.0 --port 8080")
            return
        
        print("✅ API 服务已运行\n")
        
        # 运行测试
        results = {}
        
        results['health'] = self.test_health()
        results['concurrent'] = self.test_concurrent_upload(10)
        results['large_file'] = self.test_large_file()
        results['batch'] = self.test_batch_performance([5, 10])
        # results['long_running'] = self.test_long_running(1)  # 1 分钟快速测试
        
        # 生成报告
        self.generate_report(results)
    
    def generate_report(self, results):
        """生成测试报告"""
        print("\n" + "=" * 60)
        print("📊 压力测试报告")
        print("=" * 60)
        
        print(f"\n💚 健康检查:")
        print(f"   成功: {results['health'][0]}/100")
        print(f"   QPS: {100/results['health'][2]:.2f}")
        
        print(f"\n📤 并发上传:")
        print(f"   成功: {results['concurrent'][0]}/10")
        print(f"   平均响应: {results['concurrent'][2]/10:.2f}秒")
        
        print(f"\n📁 大文件上传:")
        if results['large_file'][0] > 0:
            print(f"   ✅ 成功")
            print(f"   速度: {50/results['large_file'][2]:.2f} MB/s")
        else:
            print(f"   ❌ 失败")
        
        print(f"\n📈 批量处理:")
        for batch_size, elapsed, success in results['batch']:
            status = "✅" if success else "❌"
            print(f"   {status} 批量 {batch_size}: {elapsed:.2f}秒")
        
        print("\n" + "=" * 60)
        print("🎉 测试完成！")
        print("=" * 60)


class ScenarioTest:
    """多场景模拟"""
    
    def __init__(self, base_url=API_BASE):
        self.base_url = base_url
    
    def scenario_1_newbie_creator(self):
        """场景 1: 新手博主（单个视频，简单优化）"""
        print("\n📊 场景 1: 新手博主（单个视频优化）")
        print("-" * 60)
        
        # 1. 上传视频
        print("   1. 上传视频...")
        with open(TEST_VIDEO, 'rb') as f:
            files = {'video': ('my_first_video.mp4', f, 'video/mp4')}
            r = requests.post(f"{self.base_url}/api/v2/analyze", files=files)
        
        if r.status_code == 200:
            result = r.json()
            print(f"      ✅ 分析成功")
            print(f"      时长: {result['metadata']['duration']}秒")
            print(f"      分辨率: {result['metadata']['resolution']}")
            return True
        else:
            print(f"      ❌ 失败: {r.status_code}")
            return False
    
    def scenario_2_pro_creator(self):
        """场景 2: 专业博主（批量处理，多平台）"""
        print("\n📈 场景 2: 专业博主（批量处理，10 个视频）")
        print("-" * 60)
        
        # 批量上传
        print("   1. 批量上传 10 个视频...")
        files = []
        for i in range(10):
            f = open(TEST_VIDEO, 'rb')
            files.append(('videos', (f'video_{i}.mp4', f, 'video/mp4')))
        
        start = time.time()
        r = requests.post(
            f"{self.base_url}/api/v2/batch/analyze",
            files=files
        )
        elapsed = time.time() - start
        
        for _, (_, f, _) in files:
            f.close()
        
        if r.status_code == 200:
            result = r.json()
            print(f"      ✅ 批量分析成功")
            print(f"      总数: {result['total']}")
            print(f"      已处理: {result['processed']}")
            print(f"      耗时: {elapsed:.2f}秒")
            return True
        else:
            print(f"      ❌ 失败: {r.status_code}")
            return False
    
    def scenario_3_ecommerce_team(self):
        """场景 3: 电商团队（高频上传，性能要求高）"""
        print("\n🏪 场景 3: 电商团队（高频上传，30 个视频）")
        print("-" * 60)
        
        success = 0
        start = time.time()
        
        for i in range(30):
            try:
                with open(TEST_VIDEO, 'rb') as f:
                    files = {'video': (f'product_{i}.mp4', f, 'video/mp4')}
                    r = requests.post(f"{self.base_url}/api/v2/analyze", files=files)
                    if r.status_code == 200:
                        success += 1
            except:
                pass
        
        elapsed = time.time() - start
        print(f"   总上传: 30")
        print(f"   成功: {success}")
        print(f"   失败: {30 - success}")
        print(f"   耗时: {elapsed:.2f}秒")
        print(f"   平均: {elapsed/30:.2f}秒/个")
        print(f"   QPS: {30/elapsed:.2f}")
        
        return success == 30
    
    def run_all_scenarios(self):
        """运行所有场景"""
        print("\n🎬 多场景模拟测试")
        print("=" * 60)
        
        results = {}
        results['newbie'] = self.scenario_1_newbie_creator()
        results['pro'] = self.scenario_2_pro_creator()
        results['ecommerce'] = self.scenario_3_ecommerce_team()
        
        print("\n" + "=" * 60)
        print("📊 场景测试结果")
        print("=" * 60)
        for name, result in results.items():
            status = "✅ 通过" if result else "❌ 失败"
            print(f"   {name}: {status}")
        
        return all(results.values())


if __name__ == "__main__":
    print("🧪 VideoContentOptimizer - 压力测试 & 多场景模拟")
    print("=" * 60)
    
    # 压力测试
    stress = StressTest()
    stress.run_all_tests()
    
    # 场景模拟
    scenario = ScenarioTest()
    scenario.run_all_scenarios()
    
    print("\n🎉 全部测试完成！")
