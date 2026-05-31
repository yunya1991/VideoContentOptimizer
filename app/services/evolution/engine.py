"""
自主进化引擎 - EvolutionEngine

核心中枢，协调学习、模式识别、提示词优化和记忆管理。
灵感来源：self-improving-agent + Hermes本能进化系统

创新点：
- 视频领域专属的进化反馈循环
- 基于置信度的学习晋升机制
- 自适应提示词进化
- 错误模式免疫
"""

import json
import time
import hashlib
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path

from app.utils.logger import logger
from app.services.evolution.learner import ExperienceLearner, LearningType
from app.services.evolution.pattern import PatternRecognizer
from app.services.evolution.prompt_evolver import PromptEvolver
from app.services.evolution.memory import EvolutionMemory
from app.services.evolution.souls.soul_manager import SoulManager


class EvolutionEngine:
    """
    自主进化引擎 - 让系统越用越聪明
    
    核心机制：
    1. 经验捕获：记录每次操作的结果（成功/失败/纠正）
    2. 模式识别：从经验中提取可复用的模式
    3. 置信度晋升：高置信度模式自动晋升为系统规则
    4. 提示词进化：根据效果数据自动优化AI提示词
    5. 错误免疫：识别重复错误并生成预防策略
    """

    # 进化数据存储根目录
    EVOLUTION_DIR = Path(".evolution")
    
    # 晋升阈值
    PROMOTION_THRESHOLD = 3  # 出现次数达到3次
    PROMOTION_CONFIDENCE = 0.75  # 置信度达到75%
    PROMOTION_SPAN_DAYS = 30  # 跨度在30天内
    PROMOTION_MIN_TASKS = 2  # 至少跨2个不同任务

    def __init__(self, project_root: Optional[str] = None):
        """
        初始化进化引擎
        
        Args:
            project_root: 项目根目录，默认为当前工作目录
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.evolution_dir = self.project_root / self.EVOLUTION_DIR
        
        # 初始化子系统（注意：memory 必须先初始化，其他组件依赖它）
        self.memory = EvolutionMemory(self.evolution_dir)
        self.learner = ExperienceLearner(self.memory)
        self.pattern_recognizer = PatternRecognizer(self.memory)
        self.prompt_evolver = PromptEvolver(self.evolution_dir)
        self.soul_manager = SoulManager(self.evolution_dir)
        
        # 确保目录存在
        self._ensure_dirs()
        
        logger.info("自主进化引擎初始化完成")

    def _ensure_dirs(self):
        """确保进化系统目录结构存在"""
        dirs = [
            self.evolution_dir / "learnings",
            self.evolution_dir / "patterns",
            self.evolution_dir / "prompts",
            self.evolution_dir / "metrics",
            self.evolution_dir / "rules",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    # ============================================================
    # 核心API - 经验捕获
    # ============================================================

    def capture_success(
        self,
        task_type: str,
        context: Dict[str, Any],
        result: Any,
        approach: str,
        quality_score: Optional[float] = None,
    ) -> str:
        """
        捕获成功经验
        
        Args:
            task_type: 任务类型（analyze/optimize/regenerate）
            context: 任务上下文
            result: 任务结果
            approach: 使用的方法/策略
            quality_score: 质量评分(0-1)
            
        Returns:
            学习记录ID
        """
        learning_id = self.learner.capture_success(
            task_type=task_type,
            approach=approach,
            result_summary=str(result),
            effectiveness_score=quality_score or 0.8,
            metadata=context,
        )
        
        # 更新模式识别
        self.pattern_recognizer.record_pattern(
            pattern_key=f"{task_type}:{approach}",
            description=f"成功方法: {approach}",
            source_learning_id=learning_id,
            effectiveness=quality_score or 0.8,
        )
        
        # 更新指标
        self._update_metrics(task_type, "success", quality_score or 0.8)
        
        logger.info(f"捕获成功经验: {learning_id} | 任务: {task_type} | 评分: {quality_score}")
        
        # 记录对话到 Soul 系统
        self.soul_manager.record_conversation(
            user_message=f"任务执行成功: {task_type}",
            assistant_message=f"成功完成 {task_type} 任务，质量评分: {quality_score}",
            metadata={"task_type": task_type, "result": result, "approach": approach, "quality_score": quality_score, "learning_id": learning_id}
        )
        
        return learning_id

    def capture_error(
        self,
        task_type: str,
        context: Dict[str, Any],
        error: str,
        error_type: str = "runtime",
        recovery_approach: Optional[str] = None,
    ) -> str:
        """
        捕获错误经验
        
        Args:
            task_type: 任务类型
            context: 任务上下文
            error: 错误信息
            error_type: 错误类型（runtime/config/api/network）
            recovery_approach: 恢复方法
            
        Returns:
            学习记录ID
        """
        learning_id = self.learner.capture_error(
            task_type=task_type,
            error_pattern=error_type,
            error_message=error,
            root_cause=error_type,
            prevention_strategy=recovery_approach or "",
            severity="medium",
            metadata=context,
        )
        
        # 检查是否为重复错误模式
        error_pattern_key = self.pattern_recognizer.extract_pattern_key(error_type, error)
        similar = self.pattern_recognizer.find_similar_pattern(error_pattern_key)
        is_recurring = similar is not None
        if is_recurring:
            self._generate_error_immunity(error, error_type, recovery_approach)
        
        # 更新指标
        self._update_metrics(task_type, "error", 0.0)
        
        logger.warning(f"捕获错误经验: {learning_id} | 任务: {task_type} | 错误: {error[:50]}")
        
        # 记录对话到 Soul 系统
        self.soul_manager.record_conversation(
            user_message=f"任务执行失败: {task_type}",
            assistant_message=f"遇到错误: {error_type} - {str(error)[:200]}",
            metadata={"task_type": task_type, "error": str(error), "error_type": error_type, "recovery_approach": recovery_approach, "learning_id": learning_id}
        )
        
        return learning_id

    def capture_correction(
        self,
        task_type: str,
        original_approach: str,
        corrected_approach: str,
        context: Dict[str, Any],
        reason: str = "",
    ) -> str:
        """
        捕获纠正经验 - 用户纠正系统输出时触发
        
        Args:
            task_type: 任务类型
            original_approach: 原始方法
            corrected_approach: 纠正后的方法
            context: 任务上下文
            reason: 纠正原因
            
        Returns:
            学习记录ID
        """
        learning_id = self.learner.capture_correction(
            task_type=task_type,
            original_approach=original_approach,
            corrected_approach=corrected_approach,
            improvement_description=reason or "改进方案",
            improvement_score=0.5,
            metadata=context,
        )
        
        # 纠正经验置信度较高，直接更新模式
        self.pattern_recognizer.record_pattern(
            pattern_key=f"{task_type}:{corrected_approach}",
            description=f"纠正: {original_approach} → {corrected_approach}",
            source_learning_id=learning_id,
            effectiveness=0.9,
        )
        
        # 更新提示词
        self.prompt_evolver.learn_correction(
            task_type, original_approach, corrected_approach, reason
        )
        
        logger.info(f"捕获纠正经验: {learning_id} | 任务: {task_type}")
        
        # 记录对话到 Soul 系统
        self.soul_manager.record_conversation(
            user_message=f"方法修正: {task_type}",
            assistant_message=f"从 {original_approach} 修正为 {corrected_approach}，原因: {reason}",
            metadata={"task_type": task_type, "original_approach": original_approach, "corrected_approach": corrected_approach, "reason": reason, "learning_id": learning_id}
        )
        
        return learning_id

    def capture_feature_request(
        self,
        description: str,
        context: Dict[str, Any],
        priority: str = "medium",
    ) -> str:
        """
        捕获功能需求
        
        Args:
            description: 需求描述
            context: 上下文
            priority: 优先级（low/medium/high/critical）
            
        Returns:
            学习记录ID
        """
        learning_id = self.learner.capture_feature_request(
            feature_description=description,
            use_case=str(context),
            priority=priority,
            metadata=context,
        )
        
        logger.info(f"捕获功能需求: {learning_id} | 优先级: {priority}")
        
        # 记录对话到 Soul 系统
        self.soul_manager.record_conversation(
            user_message=f"功能请求: {description}",
            assistant_message=f"收到新功能请求，优先级: {priority}",
            metadata={"description": description, "context": context, "priority": priority, "learning_id": learning_id}
        )
        
        return learning_id

    # ============================================================
    # 核心API - 智能决策辅助
    # ============================================================

    def get_best_approach(self, task_type: str, context: Dict[str, Any]) -> Optional[Dict]:
        """
        获取最佳方法建议 - 基于历史经验推荐最优策略
        
        Args:
            task_type: 任务类型
            context: 当前任务上下文
            
        Returns:
            推荐的方法和置信度，或None
        """
        # 从记忆中检索相关经验
        relevant = self.memory.search(task_type, context)
        
        if not relevant:
            return None
        
        # 按置信度和质量评分排序
        scored = []
        for exp in relevant:
            score = exp.get("confidence", 0.5) * 0.6 + exp.get("quality_score", 0.5) * 0.4
            scored.append((exp, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        
        best = scored[0][0]
        return {
            "approach": best.get("approach", ""),
            "confidence": best.get("confidence", 0.5),
            "quality_score": best.get("quality_score", 0.5),
            "occurrences": best.get("occurrences", 1),
            "source": "evolution_engine",
        }

    def get_evolved_prompt(self, task_type: str, base_prompt: str) -> str:
        """
        获取进化后的提示词 - 基于历史效果自动优化
        
        Args:
            task_type: 任务类型
            base_prompt: 基础提示词
            
        Returns:
            优化后的提示词
        """
        return self.prompt_evolver.evolve(task_type, base_prompt)

    def get_error_prevention(self, task_type: str) -> List[Dict]:
        """
        获取错误预防策略 - 在执行任务前检查已知风险
        
        Args:
            task_type: 任务类型
            
        Returns:
            预防策略列表
        """
        return self.pattern_recognizer.get_prevention_strategies(task_type)

    def pre_task_review(self, task_type: str, context: Dict[str, Any]) -> Dict:
        """
        任务前复盘 - 在执行重要任务前回顾相关经验
        
        Args:
            task_type: 任务类型
            context: 任务上下文
            
        Returns:
            复盘结果，包含最佳方法、风险提示、相关经验
        """
        best_approach = self.get_best_approach(task_type, context)
        preventions = self.get_error_prevention(task_type)
        relevant_learnings = self.memory.search(task_type, context, limit=5)
        
        review = {
            "task_type": task_type,
            "best_approach": best_approach,
            "error_preventions": preventions,
            "relevant_learnings": [
                {
                    "id": l.get("id", ""),
                    "summary": l.get("summary", ""),
                    "confidence": l.get("confidence", 0),
                }
                for l in relevant_learnings
            ],
            "evolution_stats": self.get_stats(),
        }
        
        logger.info(f"任务前复盘: {task_type} | 最佳方法: {best_approach is not None} | 风险数: {len(preventions)}")
        return review

    # ============================================================
    # 核心API - 晋升与进化
    # ============================================================

    def check_promotions(self) -> List[Dict]:
        """
        检查并执行学习晋升 - 将高置信度学习提升为系统规则
        
        Returns:
            晋升结果列表
        """
        promotions = []
        patterns = self.pattern_recognizer.get_promotion_candidates()
        
        for pattern in patterns:
            # 生成规则
            rule = self._pattern_to_rule(pattern)
            if rule:
                # 保存规则
                self._save_rule(rule)
                # 标记模式已晋升
                self.pattern_recognizer.mark_promoted(pattern["pattern_key"], rule["id"])
                promotions.append({
                    "pattern_key": pattern["pattern_key"],
                    "rule_id": rule["id"],
                    "confidence": pattern.get("effectiveness", 0),
                    "occurrences": pattern.get("occurrence_count", 0),
                })
                logger.info(f"学习晋升: {pattern['pattern_key']} -> 规则 {rule['id']}")
        
        return promotions

    def _pattern_to_rule(self, pattern: Dict) -> Optional[Dict]:
        """将模式转换为系统规则"""
        rule_id = f"RULE-{datetime.now().strftime('%Y%m%d')}-{hashlib.md5(pattern['pattern_key'].encode()).hexdigest()[:6]}"
        
        rule = {
            "id": rule_id,
            "pattern_key": pattern["pattern_key"],
            "task_type": pattern.get("task_type", "general"),
            "approach": pattern.get("approach", ""),
            "confidence": pattern["confidence"],
            "occurrences": pattern["occurrences"],
            "created_at": datetime.now().isoformat(),
            "source_pattern": pattern,
            "rule_type": self._determine_rule_type(pattern),
            "description": self._generate_rule_description(pattern),
        }
        
        return rule

    def _determine_rule_type(self, pattern: Dict) -> str:
        """确定规则类型"""
        if pattern.get("error_type"):
            return "error_prevention"
        elif pattern.get("corrected_approach"):
            return "approach_correction"
        elif pattern.get("quality_score", 0) >= 0.8:
            return "best_practice"
        else:
            return "general_guideline"

    def _generate_rule_description(self, pattern: Dict) -> str:
        """生成规则描述"""
        rule_type = self._determine_rule_type(pattern)
        
        if rule_type == "error_prevention":
            return f"避免{pattern.get('error_type', '未知')}错误: {pattern.get('approach', '使用替代方案')}"
        elif rule_type == "approach_correction":
            return f"优先使用: {pattern.get('approach', '推荐方法')} (替代: {pattern.get('original_approach', '旧方法')})"
        elif rule_type == "best_practice":
            return f"最佳实践: {pattern.get('approach', '高效方法')} (置信度: {pattern.get('confidence', 0):.0%})"
        else:
            return f"通用指南: {pattern.get('approach', '建议方法')}"

    def _save_rule(self, rule: Dict):
        """保存规则到文件"""
        rules_dir = self.evolution_dir / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)
        
        rule_file = rules_dir / f"{rule['id'].lower()}.json"
        with open(rule_file, "w", encoding="utf-8") as f:
            json.dump(rule, f, ensure_ascii=False, indent=2)

    # ============================================================
    # 错误免疫
    # ============================================================

    def _generate_error_immunity(
        self, error: str, error_type: str, recovery: Optional[str]
    ):
        """生成错误免疫策略"""
        immunity = {
            "error_pattern": hashlib.md5(error.encode()).hexdigest()[:8],
            "error_type": error_type,
            "error_sample": error[:200],
            "recovery_approach": recovery or "unknown",
            "created_at": datetime.now().isoformat(),
            "immunity_type": "auto_generated",
        }
        
        immunity_file = self.evolution_dir / "patterns" / f"immunity-{immunity['error_pattern']}.json"
        with open(immunity_file, "w", encoding="utf-8") as f:
            json.dump(immunity, f, ensure_ascii=False, indent=2)
        
        logger.info(f"生成错误免疫策略: {immunity['error_pattern']} | 类型: {error_type}")

    # ============================================================
    # 指标与统计
    # ============================================================

    def _update_metrics(self, task_type: str, outcome: str, score: float):
        """更新进化指标"""
        metrics_file = self.evolution_dir / "metrics" / "metrics.json"
        
        metrics = {}
        if metrics_file.exists():
            with open(metrics_file, "r", encoding="utf-8") as f:
                metrics = json.load(f)
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        if "daily" not in metrics:
            metrics["daily"] = {}
        if today not in metrics["daily"]:
            metrics["daily"][today] = {"success": 0, "error": 0, "total_score": 0.0}
        
        metrics["daily"][today][outcome] = metrics["daily"][today].get(outcome, 0) + 1
        metrics["daily"][today]["total_score"] += score
        
        if "by_task" not in metrics:
            metrics["by_task"] = {}
        if task_type not in metrics["by_task"]:
            metrics["by_task"][task_type] = {"success": 0, "error": 0, "avg_score": 0.0, "count": 0}
        
        task_metrics = metrics["by_task"][task_type]
        task_metrics[outcome] = task_metrics.get(outcome, 0) + 1
        task_metrics["count"] += 1
        task_metrics["avg_score"] = (
            (task_metrics["avg_score"] * (task_metrics["count"] - 1) + score)
            / task_metrics["count"]
        )
        
        # 保留最近30天的数据
        cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        metrics["daily"] = {k: v for k, v in metrics["daily"].items() if k >= cutoff}
        
        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)

    def get_stats(self) -> Dict:
        """获取进化统计信息"""
        metrics_file = self.evolution_dir / "metrics" / "metrics.json"
        
        if not metrics_file.exists():
            return {"status": "no_data", "message": "进化系统尚未积累足够数据"}
        
        with open(metrics_file, "r", encoding="utf-8") as f:
            metrics = json.load(f)
        
        # 计算总体统计
        total_success = sum(d.get("success", 0) for d in metrics.get("daily", {}).values())
        total_error = sum(d.get("error", 0) for d in metrics.get("daily", {}).values())
        total = total_success + total_error
        
        # 计算规则数
        rules_dir = self.evolution_dir / "rules"
        rule_count = len(list(rules_dir.glob("*.json"))) if rules_dir.exists() else 0
        
        # 计算学习记录数
        learnings_stats = self.learner.get_learning_stats()
        learnings_count = learnings_stats.get("total", 0)
        
        return {
            "total_operations": total,
            "success_rate": total_success / total if total > 0 else 0,
            "total_learnings": learnings_count,
            "promoted_rules": rule_count,
            "task_breakdown": metrics.get("by_task", {}),
            "evolution_level": self._calculate_evolution_level(total_success, rule_count),
        }

    def _calculate_evolution_level(self, successes: int, rules: int) -> Dict:
        """计算进化等级"""
        score = successes * 1 + rules * 10
        
        if score >= 1000:
            level = "S"
            title = "超凡进化"
        elif score >= 500:
            level = "A"
            title = "深度进化"
        elif score >= 200:
            level = "B"
            title = "持续进化"
        elif score >= 50:
            level = "C"
            title = "初步进化"
        else:
            level = "D"
            title = "萌芽阶段"
        
        return {
            "level": level,
            "title": title,
            "score": score,
            "next_level": {
                "D": 50, "C": 200, "B": 500, "A": 1000, "S": None
            }.get(level),
        }
