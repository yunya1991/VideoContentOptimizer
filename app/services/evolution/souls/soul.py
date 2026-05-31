"""
Soul 数据模型 - 动态用户画像文档系统

Soul 是基于用户使用习惯和进化学习成果动态构建的 AI 人格文档。
它定义了 AI 在不同场景下的角色定位、专业能力、沟通风格和决策偏好。

核心设计原则：
1. 动态进化 - Soul 随使用积累和进化成果自动更新
2. 上下文限制 - Soul 文档有严格的 token 预算，确保注入 prompt 时不超限
3. 可验证性 - 每次更新都有明确的触发条件和评分依据
4. 可回滚 - 保留历史版本，支持回退到任意版本
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
import json
import hashlib


class SoulLevel(str, Enum):
    """Soul 进化等级 - 与进化引擎等级体系对齐"""
    D = "D"  # 萌芽: <50 进化分
    C = "C"  # 初步: <200 进化分
    B = "B"  # 持续: <500 进化分
    A = "A"  # 深度: <1000 进化分
    S = "S"  # 超凡: >=1000 进化分


class PersonalityTrait(str, Enum):
    """人格特质维度"""
    ANALYTICAL = "analytical"       # 分析型 - 侧重数据驱动、逻辑推理
    CREATIVE = "creative"           # 创意型 - 侧重创新思维、突破常规
    PRAGMATIC = "pragmatic"         # 务实型 - 侧重实用价值、落地执行
    EMPATHETIC = "empathetic"       # 共情型 - 侧重用户感受、情感共鸣
    PRECISE = "precise"             # 精确型 - 侧重细节把控、严谨输出
    ADAPTIVE = "adaptive"           # 适应型 - 侧重灵活应变、场景适配


@dataclass
class ExpertiseArea:
    """专业能力领域"""
    domain: str                          # 领域名称，如 "video_analysis"
    proficiency: float                   # 熟练度 0-1
    specializations: List[str] = field(default_factory=list)  # 细分专长
    proven_approaches: List[str] = field(default_factory=list)  # 验证有效的方案
    error_patterns: List[str] = field(default_factory=list)     # 已知错误模式
    evolution_score: float = 0.0         # 该领域的进化评分

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class CommunicationStyle:
    """沟通风格配置"""
    tone: str = "professional"           # 基调: professional/casual/enthusiastic/calm
    detail_level: str = "moderate"       # 细节程度: brief/moderate/detailed
    format_preference: str = "structured" # 格式偏好: structured/narrative/bullet
    language_style: str = "clear"        # 语言风格: clear/technical/creative
    emphasis: List[str] = field(default_factory=list)  # 强调重点，如 ["actionable", "data-driven"]

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class DecisionPreference:
    """决策偏好"""
    risk_tolerance: float = 0.5          # 风险容忍度 0-1
    innovation_bias: float = 0.5         # 创新倾向 0-1
    quality_threshold: float = 0.7       # 质量阈值
    preferred_strategies: List[str] = field(default_factory=list)  # 偏好策略
    avoided_patterns: List[str] = field(default_factory=list)      # 规避模式

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class SoulVersion:
    """Soul 版本记录"""
    version: str                         # 版本号，如 "1.0.0"
    timestamp: str = ""                  # 创建时间
    trigger_reason: str = ""             # 更新触发原因
    evolution_score: float = 0.0         # 更新时的进化评分
    conversation_count: int = 0          # 更新时的对话轮次
    changes: List[str] = field(default_factory=list)  # 变更摘要
    checksum: str = ""                   # 内容校验和

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Soul:
    """
    Soul 文档 - AI 的动态人格画像
    
    Soul 是一个动态文档，它定义了 AI 在 VideoContentOptimizer 中的
    角色定位、专业能力、沟通风格和决策偏好。它基于用户的实际使用习惯
    和进化系统的学习成果持续进化。
    
    更新条件：
    - 对话轮次 >= 30
    - 进化成果评分达标（根据当前等级不同阈值）
    """
    # === 身份标识 ===
    soul_id: str = "default"             # Soul 唯一标识
    name: str = "视频内容优化助手"        # 显示名称
    role_description: str = ""           # 核心角色描述（注入 prompt 的关键文本）

    # === 进化状态 ===
    level: SoulLevel = SoulLevel.D       # 当前进化等级
    evolution_score: float = 0.0         # 进化评分
    conversation_count: int = 0          # 累计对话轮次
    total_tasks_completed: int = 0       # 完成任务总数

    # === 人格特质 ===
    primary_traits: List[PersonalityTrait] = field(default_factory=lambda: [PersonalityTrait.ANALYTICAL])
    trait_weights: Dict[str, float] = field(default_factory=dict)  # 特质权重映射

    # === 专业能力 ===
    expertise: List[ExpertiseArea] = field(default_factory=list)

    # === 沟通风格 ===
    communication: CommunicationStyle = field(default_factory=CommunicationStyle)

    # === 决策偏好 ===
    decisions: DecisionPreference = field(default_factory=DecisionPreference)

    # === 进化规则摘要（从晋升规则中提取） ===
    active_rules: List[str] = field(default_factory=list)       # 当前生效的规则摘要
    prevention_strategies: List[str] = field(default_factory=list)  # 错误预防策略

    # === 版本管理 ===
    current_version: str = "0.1.0"       # 当前版本号
    version_history: List[SoulVersion] = field(default_factory=list)
    last_updated: str = ""               # 最后更新时间
    created_at: str = ""                 # 创建时间

    # === 上下文预算 ===
    max_context_tokens: int = 800        # Soul 文档最大 token 预算
    current_context_tokens: int = 0      # 当前估算 token 数

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.last_updated:
            self.last_updated = self.created_at
        if not self.trait_weights:
            self.trait_weights = {t.value: 1.0 / len(self.primary_traits) for t in self.primary_traits}

    def compute_checksum(self) -> str:
        """计算 Soul 内容的校验和"""
        content = json.dumps({
            "role_description": self.role_description,
            "level": self.level.value,
            "primary_traits": [t.value for t in self.primary_traits],
            "expertise": [e.to_dict() for e in self.expertise],
            "communication": self.communication.to_dict(),
            "decisions": self.decisions.to_dict(),
            "active_rules": self.active_rules,
        }, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def estimate_tokens(self) -> int:
        """估算 Soul 文档的 token 数（中文约 1.5 字/token）"""
        content = self.to_prompt_text()
        char_count = len(content)
        return int(char_count / 1.5)

    def to_prompt_text(self) -> str:
        """
        将 Soul 转换为可注入 prompt 的文本
        严格控制在 max_context_tokens 预算内
        """
        lines = []

        # 核心角色描述（必须包含）
        if self.role_description:
            lines.append(f"角色定位：{self.role_description}")

        # 进化等级
        lines.append(f"进化等级：{self.level.value}级（进化分：{self.evolution_score:.0f}）")

        # 人格特质
        trait_names = {
            PersonalityTrait.ANALYTICAL: "分析型",
            PersonalityTrait.CREATIVE: "创意型",
            PersonalityTrait.PRAGMATIC: "务实型",
            PersonalityTrait.EMPATHETIC: "共情型",
            PersonalityTrait.PRECISE: "精确型",
            PersonalityTrait.ADAPTIVE: "适应型",
        }
        traits_str = "、".join(trait_names.get(t, t.value) for t in self.primary_traits)
        lines.append(f"核心特质：{traits_str}")

        # 专业能力（按熟练度降序，取 top 3）
        sorted_expertise = sorted(self.expertise, key=lambda e: e.proficiency, reverse=True)[:3]
        if sorted_expertise:
            lines.append("专业能力：")
            for exp in sorted_expertise:
                spec_str = "、".join(exp.specializations[:2]) if exp.specializations else ""
                line = f"  - {exp.domain}（熟练度：{exp.proficiency:.0%}）"
                if spec_str:
                    line += f" 专长：{spec_str}"
                lines.append(line)

        # 沟通风格
        comm = self.communication
        lines.append(f"沟通风格：{comm.tone}基调，{comm.detail_level}细节，{comm.format_preference}格式")
        if comm.emphasis:
            lines.append(f"强调重点：{'、'.join(comm.emphasis[:3])}")

        # 生效规则（取 top 5）
        if self.active_rules:
            lines.append("核心规则：")
            for rule in self.active_rules[:5]:
                lines.append(f"  - {rule}")

        # 预防策略（取 top 3）
        if self.prevention_strategies:
            lines.append("风险预防：")
            for strategy in self.prevention_strategies[:3]:
                lines.append(f"  - {strategy}")

        return "\n".join(lines)

    def to_dict(self) -> Dict:
        """序列化为字典"""
        data = asdict(self)
        data["level"] = self.level.value
        data["primary_traits"] = [t.value for t in self.primary_traits]
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "Soul":
        """从字典反序列化"""
        # 处理枚举类型
        if "level" in data and isinstance(data["level"], str):
            data["level"] = SoulLevel(data["level"])
        if "primary_traits" in data:
            data["primary_traits"] = [
                PersonalityTrait(t) if isinstance(t, str) else t
                for t in data["primary_traits"]
            ]
        # 处理嵌套对象
        if "expertise" in data and isinstance(data["expertise"], list):
            data["expertise"] = [
                ExpertiseArea(**e) if isinstance(e, dict) else e
                for e in data["expertise"]
            ]
        if "communication" in data and isinstance(data["communication"], dict):
            data["communication"] = CommunicationStyle(**data["communication"])
        if "decisions" in data and isinstance(data["decisions"], dict):
            data["decisions"] = DecisionPreference(**data["decisions"])
        if "version_history" in data and isinstance(data["version_history"], list):
            data["version_history"] = [
                SoulVersion(**v) if isinstance(v, dict) else v
                for v in data["version_history"]
            ]
        return cls(**data)

    def to_json(self) -> str:
        """序列化为 JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, default=str)

    @classmethod
    def from_json(cls, json_str: str) -> "Soul":
        """从 JSON 反序列化"""
        return cls.from_dict(json.loads(json_str))
