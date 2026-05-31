"""
Soul 管理器 - 动态用户画像文档系统的核心引擎

SoulManager 负责 Soul 文档的完整生命周期管理：
1. 初始化 - 基于默认配置创建初始 Soul
2. 进化联动 - 与 EvolutionEngine 联动，根据进化成果更新 Soul
3. 对话追踪 - 追踪对话轮次，满足更新条件时触发 Soul 更新
4. Prompt 注入 - 将 Soul 文档动态注入到现有 prompt 中
5. 版本管理 - 管理 Soul 的版本历史和回滚

更新条件：
- 对话轮次 >= 30
- 进化成果评分达标（D级>=20, C级>=100, B级>=300, A级>=700, S级>=1000）
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

from app.services.evolution.souls.soul import (
    Soul,
    SoulLevel,
    SoulVersion,
    PersonalityTrait,
    ExpertiseArea,
    CommunicationStyle,
    DecisionPreference,
)

logger = logging.getLogger(__name__)


# === 更新阈值配置 ===
CONVERSATION_THRESHOLD = 30  # 对话轮次阈值

# 各等级进化评分阈值（达到该等级所需的最低进化分）
LEVEL_SCORE_THRESHOLDS = {
    SoulLevel.D: 0,
    SoulLevel.C: 50,
    SoulLevel.B: 200,
    SoulLevel.A: 500,
    SoulLevel.S: 1000,
}

# Soul 更新所需的最低进化分增量（自上次更新以来）
MIN_EVOLUTION_DELTA = {
    SoulLevel.D: 10,
    SoulLevel.C: 30,
    SoulLevel.B: 50,
    SoulLevel.A: 100,
    SoulLevel.S: 200,
}

# 任务类型到专业领域的映射
TASK_TYPE_DOMAIN_MAP = {
    "intent_detection": "video_analysis",
    "quality_assessment": "video_analysis",
    "keyword_extraction": "video_analysis",
    "script_optimization": "content_optimization",
    "title_generation": "content_optimization",
    "trend_prediction": "trend_analysis",
    "platform_adaptation": "platform_strategy",
    "video_analysis": "video_analysis",
    "content_optimization": "content_optimization",
    "trend_analysis": "trend_analysis",
    "platform_strategy": "platform_strategy",
}

# 任务类型到人格特质的映射
TASK_TYPE_TRAIT_MAP = {
    "intent_detection": [PersonalityTrait.ANALYTICAL, PersonalityTrait.PRECISE],
    "quality_assessment": [PersonalityTrait.ANALYTICAL, PersonalityTrait.PRECISE],
    "keyword_extraction": [PersonalityTrait.ANALYTICAL, PersonalityTrait.ADAPTIVE],
    "script_optimization": [PersonalityTrait.CREATIVE, PersonalityTrait.EMPATHETIC],
    "title_generation": [PersonalityTrait.CREATIVE, PersonalityTrait.PRAGMATIC],
    "trend_prediction": [PersonalityTrait.ANALYTICAL, PersonalityTrait.ADAPTIVE],
    "platform_adaptation": [PersonalityTrait.ADAPTIVE, PersonalityTrait.PRAGMATIC],
}


class SoulManager:
    """
    Soul 管理器 - 管理 AI 人格画像的完整生命周期
    
    与 EvolutionEngine 联动，基于进化成果和用户使用习惯
    动态构建和更新 Soul 文档。
    """

    def __init__(
        self,
        evolution_memory=None,
        storage_dir: str = ".evolution/souls",
        max_context_tokens: int = 800,
    ):
        """
        初始化 Soul 管理器
        
        Args:
            evolution_memory: EvolutionMemory 实例，用于读取进化数据
            storage_dir: Soul 文档存储目录
            max_context_tokens: Soul 文档最大 token 预算
        """
        self.evolution_memory = evolution_memory
        self.storage_dir = storage_dir
        self.max_context_tokens = max_context_tokens
        self._soul_cache: Optional[Soul] = None
        self._last_update_score: float = 0.0

        # 确保存储目录存在
        os.makedirs(storage_dir, exist_ok=True)
        os.makedirs(os.path.join(storage_dir, "versions"), exist_ok=True)

    # ================================================================
    # 核心 API
    # ================================================================

    def get_soul(self, soul_id: str = "default") -> Soul:
        """
        获取 Soul 文档（优先从缓存，其次从存储，最后创建默认）
        
        Args:
            soul_id: Soul 标识
            
        Returns:
            Soul 文档实例
        """
        if self._soul_cache and self._soul_cache.soul_id == soul_id:
            return self._soul_cache

        soul = self._load_soul(soul_id)
        if soul is None:
            soul = self._create_default_soul(soul_id)
            self._save_soul(soul)

        self._soul_cache = soul
        return soul

    def record_conversation(self, soul_id: str = "default") -> Dict:
        """
        记录一次对话轮次
        
        当对话轮次达到阈值时，检查是否需要更新 Soul
        
        Returns:
            包含当前状态和是否触发更新的信息
        """
        soul = self.get_soul(soul_id)
        soul.conversation_count += 1
        soul.last_updated = datetime.now().isoformat()

        result = {
            "conversation_count": soul.conversation_count,
            "threshold": CONVERSATION_THRESHOLD,
            "should_update": False,
            "reason": "",
        }

        # 检查是否满足更新条件
        if soul.conversation_count >= CONVERSATION_THRESHOLD:
            evolution_delta = soul.evolution_score - self._last_update_score
            min_delta = MIN_EVOLUTION_DELTA.get(soul.level, 10)

            if evolution_delta >= min_delta:
                result["should_update"] = True
                result["reason"] = (
                    f"对话轮次{soul.conversation_count}>={CONVERSATION_THRESHOLD}，"
                    f"进化增量{evolution_delta:.0f}>={min_delta}"
                )

        self._save_soul(soul)
        return result

    def update_soul_from_evolution(
        self,
        evolution_engine=None,
        soul_id: str = "default",
    ) -> Dict:
        """
        基于进化引擎数据更新 Soul
        
        从 EvolutionEngine 获取统计数据、晋升规则、预防策略等，
        综合更新 Soul 的各个维度。
        
        Args:
            evolution_engine: EvolutionEngine 实例
            soul_id: Soul 标识
            
        Returns:
            更新结果摘要
        """
        soul = self.get_soul(soul_id)
        old_checksum = soul.compute_checksum()
        changes = []

        try:
            # 1. 获取进化统计数据
            if evolution_engine:
                stats = evolution_engine.get_stats()
                soul.evolution_score = stats.get("total_successes", 0) * 1 + stats.get("total_rules", 0) * 10
                soul.total_tasks_completed = stats.get("total_successes", 0)

                # 2. 更新进化等级
                new_level = self._compute_level(soul.evolution_score)
                if new_level != soul.level:
                    changes.append(f"等级提升：{soul.level.value} → {new_level.value}")
                    soul.level = new_level

                # 3. 从晋升规则中提取核心规则摘要
                rules = self._load_promoted_rules()
                if rules:
                    new_rules = [r.get("description", "") for r in rules if r.get("description")]
                    if new_rules != soul.active_rules:
                        changes.append(f"更新核心规则（{len(new_rules)}条）")
                        soul.active_rules = new_rules

                # 4. 获取预防策略
                prevention_strategies = self._collect_prevention_strategies(evolution_engine)
                if prevention_strategies != soul.prevention_strategies:
                    changes.append(f"更新预防策略（{len(prevention_strategies)}条）")
                    soul.prevention_strategies = prevention_strategies

                # 5. 从学习记录中更新专业能力
                expertise_changes = self._update_expertise_from_learnings(soul)
                changes.extend(expertise_changes)

                # 6. 从任务分布中更新人格特质
                trait_changes = self._update_traits_from_usage(soul)
                changes.extend(trait_changes)

                # 7. 更新角色描述
                role_change = self._update_role_description(soul)
                if role_change:
                    changes.append(role_change)

            # 8. 估算 token 数
            soul.current_context_tokens = soul.estimate_tokens()

            # 9. 如果有变更，创建版本记录
            new_checksum = soul.compute_checksum()
            if new_checksum != old_checksum:
                version = SoulVersion(
                    version=self._increment_version(soul.current_version),
                    timestamp=datetime.now().isoformat(),
                    trigger_reason="; ".join(changes) if changes else "定期更新",
                    evolution_score=soul.evolution_score,
                    conversation_count=soul.conversation_count,
                    changes=changes,
                    checksum=new_checksum,
                )
                soul.current_version = version.version
                soul.version_history.append(version)

                # 保留最近 20 个版本
                if len(soul.version_history) > 20:
                    soul.version_history = soul.version_history[-20:]

                self._last_update_score = soul.evolution_score

            soul.last_updated = datetime.now().isoformat()
            self._save_soul(soul)

            # 保存版本快照
            if new_checksum != old_checksum:
                self._save_version_snapshot(soul)

            return {
                "updated": new_checksum != old_checksum,
                "changes": changes,
                "level": soul.level.value,
                "evolution_score": soul.evolution_score,
                "version": soul.current_version,
                "context_tokens": soul.current_context_tokens,
            }

        except Exception as e:
            logger.error(f"Soul 更新失败: {e}")
            return {
                "updated": False,
                "error": str(e),
                "changes": [],
            }

    def inject_soul_into_prompt(
        self,
        task_type: str,
        base_prompt: str,
        soul_id: str = "default",
    ) -> str:
        """
        将 Soul 文档动态注入到 prompt 中
        
        替换 base_prompt 中的硬编码角色描述，注入 Soul 动态人格。
        注入策略：
        1. 检测 base_prompt 中的角色描述行（以"你是"开头）
        2. 用 Soul 的角色描述替换
        3. 在角色描述后追加 Soul 的专业能力和规则摘要
        
        Args:
            task_type: 任务类型
            base_prompt: 原始 prompt 文本
            soul_id: Soul 标识
            
        Returns:
            注入 Soul 后的 prompt
        """
        soul = self.get_soul(soul_id)
        soul_text = soul.to_prompt_text()

        # 检查 token 预算
        estimated_tokens = soul.estimate_tokens()
        if estimated_tokens > soul.max_context_tokens:
            # 裁剪 Soul 文本以适应预算
            soul_text = self._trim_soul_text(soul, task_type)

        # 构建注入块
        soul_block = f"""【AI 人格画像 - Soul】
{soul_text}
"""

        # 策略1：替换以"你是"开头的角色描述行
        lines = base_prompt.split("\n")
        replaced = False
        new_lines = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("你是") and not replaced:
                # 替换角色描述行
                new_lines.append(soul_block)
                replaced = True
            else:
                new_lines.append(line)

        if replaced:
            return "\n".join(new_lines)

        # 策略2：如果没找到角色描述行，在 prompt 开头注入
        return soul_block + "\n" + base_prompt

    def get_soul_status(self, soul_id: str = "default") -> Dict:
        """
        获取 Soul 状态摘要
        
        Returns:
            Soul 状态信息
        """
        soul = self.get_soul(soul_id)
        return {
            "soul_id": soul.soul_id,
            "name": soul.name,
            "level": soul.level.value,
            "evolution_score": soul.evolution_score,
            "conversation_count": soul.conversation_count,
            "version": soul.current_version,
            "context_tokens": soul.current_context_tokens,
            "max_context_tokens": soul.max_context_tokens,
            "expertise_count": len(soul.expertise),
            "active_rules_count": len(soul.active_rules),
            "prevention_strategies_count": len(soul.prevention_strategies),
            "last_updated": soul.last_updated,
            "next_update_in": max(0, CONVERSATION_THRESHOLD - soul.conversation_count),
        }

    def rollback_soul(self, version: str, soul_id: str = "default") -> Dict:
        """
        回滚 Soul 到指定版本
        
        Args:
            version: 目标版本号
            soul_id: Soul 标识
            
        Returns:
            回滚结果
        """
        snapshot = self._load_version_snapshot(soul_id, version)
        if snapshot is None:
            return {"success": False, "error": f"版本 {version} 不存在"}

        soul = Soul.from_dict(snapshot)
        self._soul_cache = soul
        self._save_soul(soul)

        return {
            "success": True,
            "rolled_back_to": version,
            "level": soul.level.value,
            "evolution_score": soul.evolution_score,
        }

    # ================================================================
    # 内部方法 - Soul 更新逻辑
    # ================================================================

    def _compute_level(self, score: float) -> SoulLevel:
        """根据进化评分计算等级"""
        if score >= LEVEL_SCORE_THRESHOLDS[SoulLevel.S]:
            return SoulLevel.S
        elif score >= LEVEL_SCORE_THRESHOLDS[SoulLevel.A]:
            return SoulLevel.A
        elif score >= LEVEL_SCORE_THRESHOLDS[SoulLevel.B]:
            return SoulLevel.B
        elif score >= LEVEL_SCORE_THRESHOLDS[SoulLevel.C]:
            return SoulLevel.C
        return SoulLevel.D

    def _update_expertise_from_learnings(self, soul: Soul) -> List[str]:
        """从学习记录中更新专业能力"""
        changes = []

        if not self.evolution_memory:
            return changes

        try:
            all_learnings = self.evolution_memory.load_all_learnings()

            # 按任务类型统计
            domain_stats: Dict[str, Dict] = {}
            for learning in all_learnings:
                task_type = learning.get("task_type", "unknown")
                domain = TASK_TYPE_DOMAIN_MAP.get(task_type, task_type)

                if domain not in domain_stats:
                    domain_stats[domain] = {
                        "count": 0,
                        "successes": 0,
                        "total_effectiveness": 0.0,
                        "approaches": set(),
                        "errors": set(),
                    }

                stats = domain_stats[domain]
                stats["count"] += 1

                l_type = learning.get("type", "")
                if l_type == "success":
                    stats["successes"] += 1
                    effectiveness = learning.get("effectiveness_score", learning.get("confidence", 0.5))
                    stats["total_effectiveness"] += effectiveness
                    approach = learning.get("approach", "")
                    if approach:
                        stats["approaches"].add(approach)
                elif l_type == "error":
                    error_pattern = learning.get("error_pattern", "")
                    if error_pattern:
                        stats["errors"].add(error_pattern)

            # 更新或创建专业能力
            existing_domains = {e.domain: e for e in soul.expertise}

            for domain, stats in domain_stats.items():
                proficiency = min(1.0, stats["successes"] / max(1, stats["count"]) * 1.2)
                avg_effectiveness = (
                    stats["total_effectiveness"] / stats["successes"]
                    if stats["successes"] > 0
                    else 0.0
                )

                if domain in existing_domains:
                    exp = existing_domains[domain]
                    old_prof = exp.proficiency
                    # 滚动更新
                    exp.proficiency = round(old_prof * 0.6 + proficiency * 0.4, 3)
                    exp.specializations = list(stats["approaches"])[:5]
                    exp.error_patterns = list(stats["errors"])[:5]
                    exp.evolution_score = avg_effectiveness
                    if abs(exp.proficiency - old_prof) > 0.05:
                        changes.append(f"专业能力更新：{domain} 熟练度 {old_prof:.0%}→{exp.proficiency:.0%}")
                else:
                    new_expertise = ExpertiseArea(
                        domain=domain,
                        proficiency=round(proficiency, 3),
                        specializations=list(stats["approaches"])[:5],
                        error_patterns=list(stats["errors"])[:5],
                        evolution_score=avg_effectiveness,
                    )
                    soul.expertise.append(new_expertise)
                    changes.append(f"新增专业能力：{domain}（熟练度：{proficiency:.0%}）")

        except Exception as e:
            logger.error(f"从学习记录更新专业能力失败: {e}")

        return changes

    def _update_traits_from_usage(self, soul: Soul) -> List[str]:
        """从任务使用分布中更新人格特质"""
        changes = []

        if not self.evolution_memory:
            return changes

        try:
            all_learnings = self.evolution_memory.load_all_learnings()

            # 统计各任务类型的频次
            task_counts: Dict[str, int] = {}
            for learning in all_learnings:
                task_type = learning.get("task_type", "unknown")
                task_counts[task_type] = task_counts.get(task_type, 0) + 1

            if not task_counts:
                return changes

            # 计算特质权重
            trait_weights: Dict[str, float] = {}
            for task_type, count in task_counts.items():
                traits = TASK_TYPE_TRAIT_MAP.get(task_type, [PersonalityTrait.ANALYTICAL])
                weight = count / sum(task_counts.values())
                for trait in traits:
                    trait_weights[trait.value] = trait_weights.get(trait.value, 0.0) + weight

            # 归一化
            total_weight = sum(trait_weights.values())
            if total_weight > 0:
                trait_weights = {k: round(v / total_weight, 3) for k, v in trait_weights.items()}

            # 按权重排序，取 top 3 作为主要特质
            sorted_traits = sorted(trait_weights.items(), key=lambda x: x[1], reverse=True)
            new_primary = [PersonalityTrait(t) for t, _ in sorted_traits[:3]]

            if [t.value for t in new_primary] != [t.value for t in soul.primary_traits]:
                old_traits = "、".join(t.value for t in soul.primary_traits)
                new_traits = "、".join(t.value for t in new_primary)
                changes.append(f"核心特质调整：{old_traits} → {new_traits}")
                soul.primary_traits = new_primary

            soul.trait_weights = trait_weights

        except Exception as e:
            logger.error(f"从使用分布更新人格特质失败: {e}")

        return changes

    def _update_role_description(self, soul: Soul) -> str:
        """根据 Soul 状态动态生成角色描述"""
        trait_names = {
            PersonalityTrait.ANALYTICAL: "善于深度分析",
            PersonalityTrait.CREATIVE: "富有创意灵感",
            PersonalityTrait.PRAGMATIC: "注重实用价值",
            PersonalityTrait.EMPATHETIC: "善于情感共鸣",
            PersonalityTrait.PRECISE: "追求精确严谨",
            PersonalityTrait.ADAPTIVE: "灵活适应场景",
        }

        # 基于等级构建描述
        level_descriptions = {
            SoulLevel.D: "视频内容优化助手",
            SoulLevel.C: "经验丰富的视频内容优化顾问",
            SoulLevel.B: "资深视频内容优化专家",
            SoulLevel.A: "顶尖视频内容优化大师",
            SoulLevel.S: "视频内容优化领域的超凡导师",
        }

        base_title = level_descriptions.get(soul.level, "视频内容优化助手")

        # 基于特质构建修饰
        trait_descs = [trait_names.get(t, "") for t in soul.primary_traits[:2]]
        trait_str = "，".join(t for t in trait_descs if t)

        # 基于专业能力构建领域描述
        top_domains = sorted(soul.expertise, key=lambda e: e.proficiency, reverse=True)[:2]
        domain_str = "、".join(e.domain for e in top_domains) if top_domains else "视频内容分析与优化"

        # 组合角色描述
        if trait_str:
            new_description = f"{base_title}，{trait_str}，专注于{domain_str}"
        else:
            new_description = f"{base_title}，专注于{domain_str}"

        if new_description != soul.role_description:
            soul.role_description = new_description
            return f"角色描述更新：{new_description}"

        return ""

    def _collect_prevention_strategies(self, evolution_engine) -> List[str]:
        """从进化引擎收集所有任务类型的预防策略"""
        strategies = []
        task_types = set(TASK_TYPE_DOMAIN_MAP.keys())

        for task_type in task_types:
            try:
                task_strategies = evolution_engine.get_error_prevention(task_type)
                strategies.extend(task_strategies[:2])  # 每种任务取 top 2
            except Exception:
                continue

        return strategies[:10]  # 总共最多 10 条

    def _trim_soul_text(self, soul: Soul, task_type: str) -> str:
        """裁剪 Soul 文本以适应 token 预算"""
        lines = []

        # 必须保留：角色描述
        if soul.role_description:
            lines.append(f"角色定位：{soul.role_description}")

        # 必须保留：进化等级
        lines.append(f"进化等级：{soul.level.value}级")

        # 按相关性选择专业能力
        domain = TASK_TYPE_DOMAIN_MAP.get(task_type, "")
        relevant_expertise = [
            e for e in soul.expertise if e.domain == domain
        ] if domain else []

        if relevant_expertise:
            exp = relevant_expertise[0]
            lines.append(f"专业能力：{exp.domain}（熟练度：{exp.proficiency:.0%}）")
        elif soul.expertise:
            exp = max(soul.expertise, key=lambda e: e.proficiency)
            lines.append(f"专业能力：{exp.domain}（熟练度：{exp.proficiency:.0%}）")

        # 精简沟通风格
        lines.append(f"沟通风格：{soul.communication.tone}基调，{soul.communication.detail_level}细节")

        # 保留最相关的规则（最多 3 条）
        if soul.active_rules:
            lines.append("核心规则：")
            for rule in soul.active_rules[:3]:
                lines.append(f"  - {rule}")

        return "\n".join(lines)

    # ================================================================
    # 内部方法 - 存储操作
    # ================================================================

    def _create_default_soul(self, soul_id: str) -> Soul:
        """创建默认 Soul 文档"""
        return Soul(
            soul_id=soul_id,
            name="视频内容优化助手",
            role_description="视频内容优化助手，善于深度分析，专注于视频内容分析与优化",
            level=SoulLevel.D,
            primary_traits=[PersonalityTrait.ANALYTICAL, PersonalityTrait.ADAPTIVE],
            expertise=[
                ExpertiseArea(
                    domain="video_analysis",
                    proficiency=0.3,
                    specializations=["意图识别", "质量评估"],
                ),
                ExpertiseArea(
                    domain="content_optimization",
                    proficiency=0.2,
                    specializations=["文案优化", "标题生成"],
                ),
            ],
            communication=CommunicationStyle(
                tone="professional",
                detail_level="moderate",
                format_preference="structured",
                language_style="clear",
                emphasis=["actionable", "data-driven"],
            ),
            decisions=DecisionPreference(
                risk_tolerance=0.4,
                innovation_bias=0.5,
                quality_threshold=0.7,
            ),
            max_context_tokens=self.max_context_tokens,
        )

    def _save_soul(self, soul: Soul):
        """保存 Soul 文档到存储"""
        filepath = os.path.join(self.storage_dir, f"{soul.soul_id}.json")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(soul.to_json())
            self._soul_cache = soul
        except Exception as e:
            logger.error(f"保存 Soul 失败: {e}")

    def _load_soul(self, soul_id: str) -> Optional[Soul]:
        """从存储加载 Soul 文档"""
        filepath = os.path.join(self.storage_dir, f"{soul_id}.json")
        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Soul.from_dict(data)
        except Exception as e:
            logger.error(f"加载 Soul 失败: {e}")
            return None

    def _save_version_snapshot(self, soul: Soul):
        """保存版本快照"""
        version_dir = os.path.join(self.storage_dir, "versions")
        filepath = os.path.join(version_dir, f"{soul.soul_id}_v{soul.current_version}.json")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(soul.to_json())
        except Exception as e:
            logger.error(f"保存版本快照失败: {e}")

    def _load_version_snapshot(self, soul_id: str, version: str) -> Optional[Dict]:
        """加载版本快照"""
        filepath = os.path.join(self.storage_dir, "versions", f"{soul_id}_v{version}.json")
        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except Exception as e:
            logger.error(f"加载版本快照失败: {e}")
            return None

    def _load_promoted_rules(self) -> List[Dict]:
        """从进化记忆中加载已晋升的规则"""
        if not self.evolution_memory:
            return []

        try:
            all_patterns = self.evolution_memory.load_all("patterns")
            promoted = [
                p for p in all_patterns
                if isinstance(p, dict) and p.get("status") == "promoted"
            ]
            return promoted
        except Exception as e:
            logger.error(f"加载晋升规则失败: {e}")
            return []

    @staticmethod
    def _increment_version(version: str) -> str:
        """递增版本号（minor 版本）"""
        try:
            parts = version.split(".")
            if len(parts) == 3:
                parts[2] = str(int(parts[2]) + 1)
                return ".".join(parts)
        except (ValueError, IndexError):
            pass
        return version
