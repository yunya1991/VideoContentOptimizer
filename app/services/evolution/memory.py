"""
EvolutionMemory - 进化记忆系统

负责进化数据的持久化存储与管理。
提供统一的读写接口，支持JSON格式存储，自动目录管理。
"""

import json
import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import asdict, is_dataclass

from app.utils.logger import get_logger

logger = get_logger(__name__)


class EvolutionMemory:
    """进化记忆 - 持久化存储进化数据"""

    def __init__(self, base_path: str = ".evolution"):
        self.base_path = Path(base_path)
        self._ensure_directories()
        logger.info(f"EvolutionMemory initialized at {self.base_path.absolute()}")

    def _ensure_directories(self) -> None:
        """确保所有存储目录存在"""
        dirs = ["learnings", "patterns", "prompts", "metrics", "rules"]
        for d in dirs:
            (self.base_path / d).mkdir(parents=True, exist_ok=True)

    # ── 基础读写 ──────────────────────────────────────────

    def save(self, category: str, filename: str, data: Any) -> Path:
        """保存数据到指定类别目录"""
        dir_path = self.base_path / category
        dir_path.mkdir(parents=True, exist_ok=True)
        file_path = dir_path / filename

        # 处理 dataclass
        if is_dataclass(data) and not isinstance(data, type):
            data = asdict(data)
        elif isinstance(data, list) and data and is_dataclass(data[0]):
            data = [asdict(item) for item in data]

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        logger.debug(f"Saved {category}/{filename}")
        return file_path

    def load(self, category: str, filename: str) -> Optional[Any]:
        """从指定类别目录加载数据"""
        file_path = self.base_path / category / filename
        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_all(self, category: str) -> List[Dict[str, Any]]:
        """加载某类别的所有数据文件"""
        dir_path = self.base_path / category
        if not dir_path.exists():
            return []

        results = []
        for file_path in sorted(dir_path.glob("*.json")):
            try:
                data = self.load(category, file_path.name)
                if data is not None:
                    if isinstance(data, list):
                        results.extend(data)
                    else:
                        results.append(data)
            except Exception as e:
                logger.warning(f"Failed to load {file_path}: {e}")

        return results

    def delete(self, category: str, filename: str) -> bool:
        """删除指定文件"""
        file_path = self.base_path / category / filename
        if file_path.exists():
            file_path.unlink()
            logger.debug(f"Deleted {category}/{filename}")
            return True
        return False

    def exists(self, category: str, filename: str) -> bool:
        """检查文件是否存在"""
        return (self.base_path / category / filename).exists()

    # ── 学习记录专用 ──────────────────────────────────────

    def save_learning(self, learning_id: str, data: Dict[str, Any]) -> Path:
        """保存学习记录"""
        return self.save("learnings", f"{learning_id}.json", data)

    def load_learning(self, learning_id: str) -> Optional[Dict[str, Any]]:
        """加载单条学习记录"""
        return self.load("learnings", f"{learning_id}.json")

    def load_all_learnings(self) -> List[Dict[str, Any]]:
        """加载所有学习记录"""
        return self.load_all("learnings")

    # ── 模式专用 ──────────────────────────────────────────

    def save_pattern(self, pattern_key: str, data: Dict[str, Any]) -> Path:
        """保存模式记录"""
        safe_key = pattern_key.replace(":", "_")
        return self.save("patterns", f"{safe_key}.json", data)

    def load_pattern(self, pattern_key: str) -> Optional[Dict[str, Any]]:
        """加载模式记录"""
        safe_key = pattern_key.replace(":", "_")
        return self.load("patterns", f"{safe_key}.json")

    def load_all_patterns(self) -> List[Dict[str, Any]]:
        """加载所有模式记录"""
        return self.load_all("patterns")

    # ── 提示词专用 ────────────────────────────────────────

    def save_prompt(self, name: str, data: Dict[str, Any]) -> Path:
        """保存提示词版本"""
        return self.save("prompts", f"{name}.json", data)

    def load_prompt(self, name: str) -> Optional[Dict[str, Any]]:
        """加载提示词版本"""
        return self.load("prompts", f"{name}.json")

    def load_all_prompts(self) -> List[Dict[str, Any]]:
        """加载所有提示词版本"""
        return self.load_all("prompts")

    # ── 规则专用 ──────────────────────────────────────────

    def save_rule(self, rule_id: str, data: Dict[str, Any]) -> Path:
        """保存规则"""
        return self.save("rules", f"{rule_id}.json", data)

    def load_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """加载规则"""
        return self.load("rules", f"{rule_id}.json")

    def load_all_rules(self) -> List[Dict[str, Any]]:
        """加载所有规则"""
        return self.load_all("rules")

    # ── 指标专用 ──────────────────────────────────────────

    def save_metrics(self, date_str: str, data: Dict[str, Any]) -> Path:
        """保存每日指标"""
        return self.save("metrics", f"{date_str}.json", data)

    def load_metrics(self, date_str: str) -> Optional[Dict[str, Any]]:
        """加载每日指标"""
        return self.load("metrics", f"{date_str}.json")

    def load_all_metrics(self) -> List[Dict[str, Any]]:
        """加载所有历史指标"""
        return self.load_all("metrics")

    # ── 错误免疫专用 ──────────────────────────────────────

    def save_immunity(self, error_pattern: str, data: Dict[str, Any]) -> Path:
        """保存错误免疫记录"""
        pattern_hash = hashlib.md5(error_pattern.encode()).hexdigest()[:8]
        return self.save("learnings", f"immunity-{pattern_hash}.json", data)

    def load_immunity(self, error_pattern: str) -> Optional[Dict[str, Any]]:
        """加载错误免疫记录"""
        pattern_hash = hashlib.md5(error_pattern.encode()).hexdigest()[:8]
        return self.load("learnings", f"immunity-{pattern_hash}.json")

    def load_all_immunities(self) -> List[Dict[str, Any]]:
        """加载所有免疫记录"""
        learnings = self.load_all_learnings()
        return [l for l in learnings if l.get("type") == "immunity"]

    # ── 工具方法 ──────────────────────────────────────────

    def generate_id(self, prefix: str) -> str:
        """生成标准ID: PREFIX-YYYYMMDD-XXX"""
        today = datetime.now().strftime("%Y%m%d")
        existing = self.load_all("learnings")
        count = len([e for e in existing if e.get("id", "").startswith(f"{prefix}-{today}")])
        return f"{prefix}-{today}-{count + 1:03d}"

    def generate_rule_id(self) -> str:
        """生成规则ID: RULE-YYYYMMDD-{md5前6位}"""
        today = datetime.now().strftime("%Y%m%d")
        content = f"rule-{today}-{datetime.now().isoformat()}"
        hash_prefix = hashlib.md5(content.encode()).hexdigest()[:6]
        return f"RULE-{today}-{hash_prefix}"

    def get_stats(self) -> Dict[str, int]:
        """获取存储统计"""
        stats = {}
        for category in ["learnings", "patterns", "prompts", "metrics", "rules"]:
            dir_path = self.base_path / category
            if dir_path.exists():
                stats[category] = len(list(dir_path.glob("*.json")))
            else:
                stats[category] = 0
        return stats

    def clear_category(self, category: str) -> int:
        """清空某类别的所有数据（危险操作）"""
        dir_path = self.base_path / category
        if not dir_path.exists():
            return 0

        count = 0
        for file_path in dir_path.glob("*.json"):
            file_path.unlink()
            count += 1

        logger.warning(f"Cleared {count} files from {category}")
        return count

    def search(
        self, task_type: str, context: Optional[Dict[str, Any]] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        搜索与任务类型和上下文相关的学习记录

        Args:
            task_type: 任务类型
            context: 任务上下文（用于关键词匹配）
            limit: 返回结果数量上限

        Returns:
            按相关度排序的学习记录列表
        """
        all_learnings = self.load_all_learnings()
        if not all_learnings:
            return []

        # 按 task_type 过滤并计算相关度评分
        scored_results = []
        for learning in all_learnings:
            if not isinstance(learning, dict):
                continue

            # task_type 匹配检查
            learning_type = learning.get("task_type", learning.get("type", ""))
            if learning_type and learning_type != task_type:
                continue

            # 计算相关度评分
            score = 0.0

            # task_type 完全匹配加分
            if learning_type == task_type:
                score += 0.5

            # context 关键词匹配
            if context and isinstance(context, dict):
                context_str = str(context).lower()
                # 检查学习记录中的关键词字段
                for field in ["summary", "description", "error_type", "approach", "solution"]:
                    field_value = learning.get(field, "")
                    if field_value and isinstance(field_value, str):
                        field_lower = field_value.lower()
                        # 简单关键词匹配：context 中的词出现在字段中
                        for word in context_str.split():
                            if len(word) > 2 and word in field_lower:
                                score += 0.1

            # 置信度加权
            confidence = learning.get("confidence", 0.5)
            score += confidence * 0.3

            # 质量评分加权
            quality = learning.get("quality_score", 0.5)
            score += quality * 0.2

            scored_results.append((learning, score))

        # 按评分降序排序
        scored_results.sort(key=lambda x: x[1], reverse=True)

        # 返回 top N 结果
        return [item[0] for item in scored_results[:limit]]
