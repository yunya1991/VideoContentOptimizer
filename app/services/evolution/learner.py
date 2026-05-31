"""
ExperienceLearner - 经验学习系统

负责捕获、分类和存储各类经验数据。
支持成功模式、错误教训、修正方案、功能请求四种学习类型。
"""

import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from app.utils.logger import get_logger
from app.services.evolution.memory import EvolutionMemory

logger = get_logger(__name__)


class LearningType(Enum):
    """学习类型枚举"""
    SUCCESS = "success"           # 成功经验
    ERROR = "error"               # 错误教训
    CORRECTION = "correction"     # 修正方案
    FEATURE_REQUEST = "feature"   # 功能请求


class ExperienceLearner:
    """经验学习者 - 捕获和存储各类经验"""

    def __init__(self, memory: EvolutionMemory):
        self.memory = memory
        logger.info("ExperienceLearner initialized")

    def capture_success(
        self,
        task_type: str,
        approach: str,
        result_summary: str,
        effectiveness_score: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        捕获成功经验

        Args:
            task_type: 任务类型，如 "video_analysis", "content_optimization"
            approach: 采用的方法/策略描述
            result_summary: 结果摘要
            effectiveness_score: 效果评分 0.0-1.0
            metadata: 额外元数据

        Returns:
            learning_id: 学习记录ID
        """
        learning_id = self.memory.generate_id("LEARN")
        data = {
            "id": learning_id,
            "type": LearningType.SUCCESS.value,
            "task_type": task_type,
            "approach": approach,
            "result_summary": result_summary,
            "effectiveness_score": effectiveness_score,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
            "occurrence_count": 1,
            "confidence": effectiveness_score,
        }

        self.memory.save_learning(learning_id, data)
        logger.info(f"Captured success: {learning_id} for {task_type}")
        return learning_id

    def capture_error(
        self,
        task_type: str,
        error_pattern: str,
        error_message: str,
        root_cause: str,
        prevention_strategy: str,
        severity: str = "medium",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        捕获错误教训

        Args:
            task_type: 任务类型
            error_pattern: 错误模式标识
            error_message: 错误信息
            root_cause: 根本原因分析
            prevention_strategy: 预防策略
            severity: 严重程度 low/medium/high/critical
            metadata: 额外元数据

        Returns:
            learning_id: 学习记录ID
        """
        learning_id = self.memory.generate_id("ERROR")
        data = {
            "id": learning_id,
            "type": LearningType.ERROR.value,
            "task_type": task_type,
            "error_pattern": error_pattern,
            "error_message": error_message,
            "root_cause": root_cause,
            "prevention_strategy": prevention_strategy,
            "severity": severity,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
            "occurrence_count": 1,
            "confidence": 0.5,  # 初始置信度
            "immune": False,
        }

        self.memory.save_learning(learning_id, data)
        logger.info(f"Captured error: {learning_id} - {error_pattern}")
        return learning_id

    def capture_correction(
        self,
        task_type: str,
        original_approach: str,
        corrected_approach: str,
        improvement_description: str,
        improvement_score: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        捕获修正方案

        Args:
            task_type: 任务类型
            original_approach: 原始方法
            corrected_approach: 修正后的方法
            improvement_description: 改进说明
            improvement_score: 改进幅度 0.0-1.0
            metadata: 额外元数据

        Returns:
            learning_id: 学习记录ID
        """
        learning_id = self.memory.generate_id("CORR")
        data = {
            "id": learning_id,
            "type": LearningType.CORRECTION.value,
            "task_type": task_type,
            "original_approach": original_approach,
            "corrected_approach": corrected_approach,
            "improvement_description": improvement_description,
            "improvement_score": improvement_score,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
            "occurrence_count": 1,
            "confidence": improvement_score,
        }

        self.memory.save_learning(learning_id, data)
        logger.info(f"Captured correction: {learning_id} for {task_type}")
        return learning_id

    def capture_feature_request(
        self,
        feature_description: str,
        use_case: str,
        priority: str = "medium",
        suggested_approach: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        捕获功能请求

        Args:
            feature_description: 功能描述
            use_case: 使用场景
            priority: 优先级 low/medium/high/urgent
            suggested_approach: 建议实现方案
            metadata: 额外元数据

        Returns:
            learning_id: 学习记录ID
        """
        learning_id = self.memory.generate_id("FEAT")
        data = {
            "id": learning_id,
            "type": LearningType.FEATURE_REQUEST.value,
            "feature_description": feature_description,
            "use_case": use_case,
            "priority": priority,
            "suggested_approach": suggested_approach,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
            "status": "pending",  # pending/accepted/rejected/implemented
            "occurrence_count": 1,
        }

        self.memory.save_learning(learning_id, data)
        logger.info(f"Captured feature request: {learning_id}")
        return learning_id

    def update_learning(self, learning_id: str, updates: Dict[str, Any]) -> bool:
        """更新学习记录"""
        data = self.memory.load_learning(learning_id)
        if data is None:
            logger.warning(f"Learning not found: {learning_id}")
            return False

        data.update(updates)
        data["updated_at"] = datetime.now().isoformat()
        self.memory.save_learning(learning_id, data)
        logger.debug(f"Updated learning: {learning_id}")
        return True

    def increment_occurrence(self, learning_id: str) -> bool:
        """增加学习记录的出现次数"""
        data = self.memory.load_learning(learning_id)
        if data is None:
            return False

        count = data.get("occurrence_count", 1) + 1
        confidence = min(0.95, data.get("confidence", 0.5) + 0.05)

        return self.update_learning(learning_id, {
            "occurrence_count": count,
            "confidence": confidence,
            "last_occurred": datetime.now().isoformat(),
        })

    def get_learnings_by_type(self, learning_type: LearningType) -> List[Dict[str, Any]]:
        """按类型获取学习记录"""
        all_learnings = self.memory.load_all_learnings()
        return [l for l in all_learnings if l.get("type") == learning_type.value]

    def get_learnings_by_task(self, task_type: str) -> List[Dict[str, Any]]:
        """按任务类型获取学习记录"""
        all_learnings = self.memory.load_all_learnings()
        return [l for l in all_learnings if l.get("task_type") == task_type]

    def get_high_confidence_learnings(self, threshold: float = 0.75) -> List[Dict[str, Any]]:
        """获取高置信度学习记录"""
        all_learnings = self.memory.load_all_learnings()
        return [l for l in all_learnings if l.get("confidence", 0) >= threshold]

    def get_recent_learnings(self, days: int = 7) -> List[Dict[str, Any]]:
        """获取最近N天的学习记录"""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=days)
        all_learnings = self.memory.load_all_learnings()

        recent = []
        for l in all_learnings:
            try:
                ts = datetime.fromisoformat(l.get("timestamp", ""))
                if ts >= cutoff:
                    recent.append(l)
            except (ValueError, TypeError):
                continue

        return sorted(recent, key=lambda x: x.get("timestamp", ""), reverse=True)

    def get_learning_stats(self) -> Dict[str, Any]:
        """获取学习统计"""
        all_learnings = self.memory.load_all_learnings()
        stats = {
            "total": len(all_learnings),
            "by_type": {},
            "by_task": {},
            "high_confidence": 0,
            "recent_7d": 0,
        }

        for l in all_learnings:
            l_type = l.get("type", "unknown")
            stats["by_type"][l_type] = stats["by_type"].get(l_type, 0) + 1

            task = l.get("task_type", "unknown")
            stats["by_task"][task] = stats["by_task"].get(task, 0) + 1

            if l.get("confidence", 0) >= 0.75:
                stats["high_confidence"] += 1

        stats["recent_7d"] = len(self.get_recent_learnings(7))
        return stats
