"""
自主进化系统 - Self-Evolving System

让VideoContentOptimizer越用越聪明的核心引擎。
基于经验学习、模式识别、置信度评分和自适应优化的持续进化机制。

创新特性：
1. 视频领域专属进化 - 基于视频分析/优化结果的反馈学习
2. 置信度评分晋升 - 高置信度学习自动晋升为系统规则
3. 自适应提示词 - 根据历史效果自动优化AI提示词
4. 错误模式免疫 - 识别并预防重复错误
5. 跨会话记忆 - 持久化学习成果，跨会话复用
"""

from app.services.evolution.engine import EvolutionEngine
from app.services.evolution.learner import ExperienceLearner
from app.services.evolution.pattern import PatternRecognizer
from app.services.evolution.prompt_evolver import PromptEvolver
from app.services.evolution.memory import EvolutionMemory

__all__ = [
    "EvolutionEngine",
    "ExperienceLearner",
    "PatternRecognizer",
    "PromptEvolver",
    "EvolutionMemory",
]
