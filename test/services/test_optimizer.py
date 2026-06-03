"""
测试优化模块
"""

import pytest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.services.optimizer.script_optimizer import ScriptOptimizer
from app.services.optimizer.title_generator import TitleGenerator
from app.models.schema import VideoIntent

class MockLLMClient:
    """模拟 LLM 客户端用于测试"""
    
    def generate(self, prompt: str) -> str:
        """模拟 LLM 生成"""
        if "文案优化" in prompt or "优化" in prompt:
            return '{"optimized_script": "优化后的文案示例", "changes": ["改进点1", "改进点2"], "readability_improvement": 15, "engagement_increase": 20}'
        elif "标题" in prompt:
            return '{"titles": [{"title": "测试标题1", "style": "curiosity_gap", "estimated_ctr": 0.15, "rationale": "吸引好奇心"}]}'
        else:
            return '{"result": "mock response"}'
    
    def generate_json(self, prompt: str, **kwargs) -> dict:
        """模拟 JSON 生成"""
        response = self.generate(prompt)
        import json
        try:
            return json.loads(response)
        except:
            return {"result": response}

class TestScriptOptimizer:
    """测试文案优化器"""
    
    def setup_method(self):
        """测试前准备"""
        self.llm_client = MockLLMClient()
        self.optimizer = ScriptOptimizer(llm_client=self.llm_client)
        
        self.test_intent = VideoIntent(
            category="教育",
            sub_category="编程教学",
            target_audience="初学者",
            emotion="励志",
            confidence=0.9,
            core_message="30天学会编程"
        )
    
    def test_optimize_script(self):
        """测试文案优化"""
        original_script = "今天教大家如何在30天内学会编程"
        
        result = self.optimizer.optimize_script(
            original_script=original_script,
            intent=self.test_intent,
            target_platform="douyin"
        )
        
        assert result is not None
        assert "optimized_script" in result or "optimized_script" in str(result)
    
    def test_optimize_without_llm(self):
        """测试没有 LLM 客户端的情况"""
        optimizer = ScriptOptimizer(llm_client=None)
        
        result = optimizer.optimize_script(
            original_script="测试文案",
            intent=self.test_intent
        )
        
        assert result is not None
        assert "optimized_script" in result
    
    def test_optimize_for_platform(self):
        """测试平台优化"""
        result = self.optimizer.optimize_for_platform(
            script="测试文案",
            platform="xiaohongshu",
            intent=self.test_intent
        )
        
        assert isinstance(result, str)
    
    def test_generate_multiple_versions(self):
        """测试生成多个版本"""
        versions = self.optimizer.generate_multiple_versions(
            original_script="测试文案",
            intent=self.test_intent,
            num_versions=3
        )
        
        assert isinstance(versions, list)
        assert len(versions) <= 3

class TestTitleGenerator:
    """测试标题生成器"""
    
    def setup_method(self):
        """测试前准备"""
        self.llm_client = MockLLMClient()
        self.generator = TitleGenerator(llm_client=self.llm_client)
        
        self.test_intent = VideoIntent(
            category="教育",
            sub_category="编程教学",
            target_audience="初学者",
            emotion="实用",
            confidence=0.85,
            core_message="学编程"
        )
    
    def test_generate_titles(self):
        """测试标题生成"""
        transcript = "今天教大家如何在30天内学会编程，从零基础到找到工作"
        keywords = ["编程", "30天", "零基础", "找工作"]
        
        titles = self.generator.generate_titles(
            transcript=transcript,
            keywords=keywords,
            intent=self.test_intent,
            num_titles=3,
            target_platform="douyin"
        )
        
        assert isinstance(titles, list)
        assert len(titles) <= 3
    
    def test_title_styles(self):
        """测试标题风格"""
        assert "curiosity_gap" in TitleGenerator.TITLE_STYLES
        assert "emotional" in TitleGenerator.TITLE_STYLES
        assert "practical" in TitleGenerator.TITLE_STYLES
        assert "benefit" in TitleGenerator.TITLE_STYLES
    
    def test_generate_without_llm(self):
        """测试没有 LLM 的情况"""
        generator = TitleGenerator(llm_client=None)
        
        titles = generator.generate_titles(
            transcript="测试内容",
            keywords=["测试"],
            intent=self.test_intent
        )
        
        assert isinstance(titles, list)
        assert len(titles) > 0
    
    def test_estimate_ctr(self):
        """测试 CTR 估算"""
        ctr = self.generator.estimate_ctr("30天学会编程，年薪涨20万！", "benefit")
        
        assert 0 <= ctr <= 1.0
    
    def test_check_platform_compliance(self):
        """测试平台合规性检查"""
        # 测试正常标题
        is_compliant, issues = self.generator.check_platform_compliance(
            "30天学会编程",
            "douyin"
        )
        
        assert isinstance(is_compliant, bool)
        assert isinstance(issues, list)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
