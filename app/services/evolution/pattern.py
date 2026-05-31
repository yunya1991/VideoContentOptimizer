"""
PatternRecognizer - 模式识别系统

负责从经验中提取模式、检测重复、识别晋升候选。
支持基于category:action的键去重，以及相似度匹配。
"""

import hashlib
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.utils.logger import get_logger
from app.services.evolution.memory import EvolutionMemory

logger = get_logger(__name__)


class PatternRecognizer:
    """模式识别器 - 提取、去重和评估模式"""

    # 晋升阈值
    PROMOTION_THRESHOLD = 3          # 最少出现次数
    PROMOTION_CONFIDENCE = 0.75      # 最低置信度
    PROMOTION_SPAN_DAYS = 30         # 时间跨度（天）
    PROMOTION_MIN_TASKS = 2          # 最少涉及任务数

    def __init__(self, memory: EvolutionMemory):
        self.memory = memory
        logger.info("PatternRecognizer initialized")

    def extract_pattern_key(self, task_type: str, action: str) -> str:
        """
        提取模式键 - category:action 格式

        Args:
            task_type: 任务类别
            action: 具体动作/方法

        Returns:
            pattern_key: 如 "video_analysis:scene_detection"
        """
        # 规范化处理
        category = self._normalize(task_type)
        action_key = self._normalize(action)
        return f"{category}:{action_key}"

    def _normalize(self, text: str) -> str:
        """规范化文本为模式键"""
        text = text.lower().strip()
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', '_', text)
        return text[:50]

    def find_similar_pattern(self, pattern_key: str) -> Optional[Dict[str, Any]]:
        """
        查找相似模式（支持模糊匹配）

        Args:
            pattern_key: 新模式键

        Returns:
            相似的模式记录，无则返回None
        """
        category, action = pattern_key.split(":", 1)
        all_patterns = self.memory.load_all_patterns()

        best_match = None
        best_score = 0.0

        for pattern in all_patterns:
            existing_key = pattern.get("pattern_key", "")
            score = self._calculate_similarity(pattern_key, existing_key)
            if score > 0.8 and score > best_score:  # 80%相似度阈值
                best_score = score
                best_match = pattern

        return best_match

    def _calculate_similarity(self, key1: str, key2: str) -> float:
        """计算两个模式键的相似度 (0.0-1.0)"""
        if key1 == key2:
            return 1.0

        # 简单Jaccard相似度
        set1 = set(key1.split("_"))
        set2 = set(key2.split("_"))

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        if union == 0:
            return 0.0

        return intersection / union

    def record_pattern(
        self,
        pattern_key: str,
        description: str,
        source_learning_id: str,
        effectiveness: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, bool]:
        """
        记录模式（自动去重）

        Args:
            pattern_key: 模式键
            description: 模式描述
            source_learning_id: 来源学习记录ID
            effectiveness: 效果评分
            metadata: 元数据

        Returns:
            (pattern_key, is_new): 模式键和是否为新模式
        """
        existing = self.memory.load_pattern(pattern_key)

        if existing:
            # 更新现有模式
            existing["occurrence_count"] = existing.get("occurrence_count", 1) + 1
            existing["effectiveness"] = (
                existing.get("effectiveness", 0.5) * 0.7 + effectiveness * 0.3
            )
            existing["source_ids"] = existing.get("source_ids", []) + [source_learning_id]
            existing["last_seen"] = datetime.now().isoformat()

            # 更新涉及的任务类型
            if metadata and "task_type" in metadata:
                tasks = set(existing.get("related_tasks", []))
                tasks.add(metadata["task_type"])
                existing["related_tasks"] = list(tasks)

            self.memory.save_pattern(pattern_key, existing)
            logger.debug(f"Updated pattern: {pattern_key} (count={existing['occurrence_count']})")
            return pattern_key, False

        # 创建新模式
        data = {
            "pattern_key": pattern_key,
            "description": description,
            "source_ids": [source_learning_id],
            "effectiveness": effectiveness,
            "occurrence_count": 1,
            "created_at": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "related_tasks": [metadata.get("task_type", "unknown")] if metadata else ["unknown"],
            "promotion_status": "candidate",  # candidate/promoted/rejected
            "metadata": metadata or {},
        }

        self.memory.save_pattern(pattern_key, data)
        logger.info(f"New pattern recorded: {pattern_key}")
        return pattern_key, True

    def get_promotion_candidates(self) -> List[Dict[str, Any]]:
        """
        获取符合晋升条件的模式候选

        晋升条件：
        1. 出现次数 >= PROMOTION_THRESHOLD (3)
        2. 置信度/效果 >= PROMOTION_CONFIDENCE (0.75)
        3. 时间跨度 >= PROMOTION_SPAN_DAYS (30天)
        4. 涉及任务数 >= PROMOTION_MIN_TASKS (2)
        """
        all_patterns = self.memory.load_all_patterns()
        candidates = []
        cutoff = datetime.now() - timedelta(days=self.PROMOTION_SPAN_DAYS)

        for pattern in all_patterns:
            if pattern.get("promotion_status") != "candidate":
                continue

            # 检查出现次数
            count = pattern.get("occurrence_count", 0)
            if count < self.PROMOTION_THRESHOLD:
                continue

            # 检查效果评分
            effectiveness = pattern.get("effectiveness", 0)
            if effectiveness < self.PROMOTION_CONFIDENCE:
                continue

            # 检查时间跨度
            created = pattern.get("created_at", "")
            try:
                created_dt = datetime.fromisoformat(created)
                if created_dt > cutoff:
                    continue
            except (ValueError, TypeError):
                continue

            # 检查涉及任务数
            tasks = pattern.get("related_tasks", [])
            if len(set(tasks)) < self.PROMOTION_MIN_TASKS:
                continue

            candidates.append(pattern)

        # 按效果评分排序
        candidates.sort(key=lambda x: x.get("effectiveness", 0), reverse=True)
        return candidates

    def mark_promoted(self, pattern_key: str, rule_id: str) -> bool:
        """标记模式已晋升"""
        pattern = self.memory.load_pattern(pattern_key)
        if not pattern:
            return False

        pattern["promotion_status"] = "promoted"
        pattern["promoted_at"] = datetime.now().isoformat()
        pattern["rule_id"] = rule_id
        self.memory.save_pattern(pattern_key, pattern)
        logger.info(f"Pattern promoted: {pattern_key} -> {rule_id}")
        return True

    def get_patterns_by_task(self, task_type: str) -> List[Dict[str, Any]]:
        """获取指定任务类型的所有模式"""
        all_patterns = self.memory.load_all_patterns()
        return [
            p for p in all_patterns
            if task_type in p.get("related_tasks", [])
        ]

    def get_top_patterns(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取效果最好的模式"""
        all_patterns = self.memory.load_all_patterns()
        sorted_patterns = sorted(
            all_patterns,
            key=lambda x: x.get("effectiveness", 0),
            reverse=True
        )
        return sorted_patterns[:limit]

    def analyze_pattern_trends(self, days: int = 7) -> Dict[str, Any]:
        """分析模式趋势"""
        cutoff = datetime.now() - timedelta(days=days)
        all_patterns = self.memory.load_all_patterns()

        new_patterns = 0
        active_patterns = 0
        promoted_count = 0
        task_distribution = {}

        for p in all_patterns:
            # 统计晋升
            if p.get("promotion_status") == "promoted":
                promoted_count += 1

            # 统计活跃
            last_seen = p.get("last_seen", "")
            try:
                last_dt = datetime.fromisoformat(last_seen)
                if last_dt >= cutoff:
                    active_patterns += 1
            except (ValueError, TypeError):
                pass

            # 统计新增
            created = p.get("created_at", "")
            try:
                created_dt = datetime.fromisoformat(created)
                if created_dt >= cutoff:
                    new_patterns += 1
            except (ValueError, TypeError):
                pass

            # 任务分布
            for task in p.get("related_tasks", []):
                task_distribution[task] = task_distribution.get(task, 0) + 1

        return {
            "total_patterns": len(all_patterns),
            "new_patterns_7d": new_patterns,
            "active_patterns_7d": active_patterns,
            "promoted_patterns": promoted_count,
            "task_distribution": task_distribution,
            "promotion_candidates": len(self.get_promotion_candidates()),
        }

    def deduplicate_learning(self, learning: Dict[str, Any]) -> Optional[str]:
        """
        对学习记录进行去重检测

        Returns:
            如果找到相似模式，返回模式键；否则返回None
        """
        task_type = learning.get("task_type", "")
        approach = learning.get("approach", "")
        if not task_type or not approach:
            return None

        pattern_key = self.extract_pattern_key(task_type, approach)
        similar = self.find_similar_pattern(pattern_key)

        if similar:
            return similar.get("pattern_key")

        return None

    def get_prevention_strategies(self, task_type: str) -> List[Dict[str, Any]]:
        """
        获取指定任务类型的错误预防策略。

        基于已识别的模式，提取高置信度的预防策略，
        优先返回已晋升(promoted)的模式，其次返回高频出现的候选模式。

        Args:
            task_type: 任务类型，如 "script_optimization"、"content_analysis" 等

        Returns:
            预防策略列表，按优先级排序，每条策略包含：
            - pattern_key: 模式标识
            - description: 模式描述
            - effectiveness: 效果评分 (0-1)
            - occurrence_count: 出现次数
            - prevention_tip: 预防建议
            - promotion_status: 晋升状态
            - related_tasks: 关联任务列表
        """
        patterns = self.get_patterns_by_task(task_type)

        if not patterns:
            return []

        strategies: List[Dict[str, Any]] = []

        for pattern in patterns:
            effectiveness = pattern.get("effectiveness", 0.0)
            occurrence_count = pattern.get("occurrence_count", 0)
            promotion_status = pattern.get("promotion_status", "candidate")

            # 跳过低效和低频模式
            if effectiveness < 0.5 or occurrence_count < 2:
                continue

            # 跳过已拒绝的模式
            if promotion_status == "rejected":
                continue

            description = pattern.get("description", "")
            pattern_key = pattern.get("pattern_key", "")

            # 根据模式信息生成预防建议
            prevention_tip = self._generate_prevention_tip(
                pattern_key=pattern_key,
                description=description,
                effectiveness=effectiveness,
                occurrence_count=occurrence_count,
                promotion_status=promotion_status,
            )

            strategy = {
                "pattern_key": pattern_key,
                "description": description,
                "effectiveness": effectiveness,
                "occurrence_count": occurrence_count,
                "prevention_tip": prevention_tip,
                "promotion_status": promotion_status,
                "related_tasks": pattern.get("related_tasks", []),
            }
            strategies.append(strategy)

        # 排序：已晋升的优先，然后按效果评分降序，再按出现次数降序
        strategies.sort(
            key=lambda s: (
                0 if s["promotion_status"] == "promoted" else 1,
                -s["effectiveness"],
                -s["occurrence_count"],
            )
        )

        return strategies

    def _generate_prevention_tip(
        self,
        pattern_key: str,
        description: str,
        effectiveness: float,
        occurrence_count: int,
        promotion_status: str,
    ) -> str:
        """
        根据模式信息生成预防建议文本。

        Args:
            pattern_key: 模式键
            description: 模式描述
            effectiveness: 效果评分
            occurrence_count: 出现次数
            promotion_status: 晋升状态

        Returns:
            预防建议文本
        """
        # 优先使用模式描述作为建议基础
        if description:
            tip = f"注意: {description}"
        else:
            # 从 pattern_key 提取可读信息
            parts = pattern_key.split(":")
            if len(parts) >= 2:
                category, action = parts[0], parts[1]
                tip = f"注意 {category} 场景下的 {action} 问题"
            else:
                tip = f"注意已识别的模式: {pattern_key}"

        # 根据置信度附加建议强度
        if promotion_status == "promoted":
            tip += "（已验证的高频模式，强烈建议规避）"
        elif effectiveness >= self.PROMOTION_CONFIDENCE and occurrence_count >= self.PROMOTION_THRESHOLD:
            tip += "（高频模式，建议重点关注）"
        else:
            tip += "（观察中的模式，建议留意）"

        return tip
