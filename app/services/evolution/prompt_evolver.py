"""
提示词进化器 - PromptEvolver

基于历史修正学习和效果反馈，自动优化AI提示词。
核心能力：
1. 修正学习 - 从人工/自动修正中学习，优化提示词表达
2. 版本管理 - 维护提示词版本历史，支持回滚
3. 效果追踪 - 追踪不同提示词版本的效果评分
4. 智能进化 - 基于效果数据自动选择最佳提示词
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict

from app.services.evolution.memory import EvolutionMemory


@dataclass
class PromptVersion:
    """提示词版本记录"""
    version_id: str
    task_type: str
    prompt_text: str
    created_at: str
    effectiveness_score: float = 0.5
    usage_count: int = 0
    corrections_applied: int = 0
    parent_version: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PromptCorrection:
    """提示词修正记录"""
    correction_id: str
    task_type: str
    original_prompt: str
    corrected_prompt: str
    reason: str
    timestamp: str
    applied: bool = False
    effectiveness_delta: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class PromptEvolver:
    """
    提示词进化器
    
    通过持续学习修正和追踪效果，自动优化AI提示词质量。
    每个任务类型维护独立的提示词版本链。
    """
    
    # 进化阈值
    EVOLUTION_THRESHOLD = 0.6  # 效果评分阈值，低于此值触发进化
    CORRECTION_WEIGHT = 0.3    # 修正学习权重
    USAGE_WEIGHT = 0.2         # 使用频率权重
    EFFECTIVENESS_WEIGHT = 0.5 # 效果评分权重
    
    # 最大版本历史数
    MAX_VERSION_HISTORY = 10
    
    def __init__(self, evolution_dir: Path):
        """
        初始化提示词进化器
        
        Args:
            evolution_dir: 进化数据根目录路径
        """
        self.evolution_dir = Path(evolution_dir)
        self.prompts_dir = self.evolution_dir / "prompts"
        self.prompts_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化内存存储
        self.memory = EvolutionMemory(self.evolution_dir)
        
        # 内存缓存：task_type -> 当前最佳提示词版本
        self._current_versions: Dict[str, PromptVersion] = {}
        
        # 加载现有提示词
        self._load_all_prompts()
    
    def _load_all_prompts(self):
        """加载所有已保存的提示词版本"""
        try:
            all_prompts = self.memory.load_all_prompts()
            for data in all_prompts:
                # 通过数据字段判断是否为当前版本记录
                # 当前版本记录包含 version_id 和 task_type 字段，且无 correction_id
                if isinstance(data, dict) and "version_id" in data and "task_type" in data and "correction_id" not in data:
                    task_type = data.get("task_type", "")
                    is_current = data.get("is_current", True)  # 默认视为当前版本
                    if is_current and task_type:
                        version = self._dict_to_version(data)
                        self._current_versions[task_type] = version
        except Exception as e:
            print(f"[PromptEvolver] 加载提示词失败: {e}")
    
    def _dict_to_version(self, data: Dict) -> PromptVersion:
        """将字典转换为PromptVersion"""
        return PromptVersion(
            version_id=data.get("version_id", ""),
            task_type=data.get("task_type", ""),
            prompt_text=data.get("prompt_text", ""),
            created_at=data.get("created_at", datetime.now().isoformat()),
            effectiveness_score=data.get("effectiveness_score", 0.5),
            usage_count=data.get("usage_count", 0),
            corrections_applied=data.get("corrections_applied", 0),
            parent_version=data.get("parent_version"),
            metadata=data.get("metadata", {}),
        )
    
    def _generate_version_id(self, task_type: str, prompt_text: str) -> str:
        """生成版本ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        content_hash = hashlib.md5(prompt_text.encode()).hexdigest()[:6]
        task_hash = hashlib.md5(task_type.encode()).hexdigest()[:4]
        return f"PROMPT-{task_hash}-{timestamp}-{content_hash}"
    
    def _generate_correction_id(self) -> str:
        """生成修正记录ID"""
        return self.memory.generate_id("CORR-PROMPT")
    
    def learn_correction(
        self,
        task_type: str,
        original: str,
        corrected: str,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        学习提示词修正
        
        记录原始提示词与修正后提示词的差异，用于后续进化。
        
        Args:
            task_type: 任务类型（如 "video_analysis", "content_optimization"）
            original: 原始提示词
            corrected: 修正后的提示词
            reason: 修正原因
            metadata: 额外元数据
            
        Returns:
            correction_id: 修正记录ID
        """
        correction_id = self._generate_correction_id()
        
        correction = PromptCorrection(
            correction_id=correction_id,
            task_type=task_type,
            original_prompt=original,
            corrected_prompt=corrected,
            reason=reason,
            timestamp=datetime.now().isoformat(),
            applied=False,
            metadata=metadata or {},
        )
        
        # 保存修正记录
        self.memory.save(
            "prompts",
            f"correction_{correction_id}.json",
            asdict(correction),
        )
        
        # 尝试应用修正到当前版本
        self._apply_correction(task_type, correction)
        
        print(f"[PromptEvolver] 学习修正: {correction_id} for {task_type}")
        return correction_id
    
    def _apply_correction(self, task_type: str, correction: PromptCorrection):
        """
        应用修正到当前提示词版本
        
        如果修正针对当前版本，则创建新版本。
        """
        current = self._current_versions.get(task_type)
        
        if current and current.prompt_text == correction.original_prompt:
            # 修正直接针对当前版本，创建进化版本
            new_version = self._create_evolved_version(
                task_type,
                current,
                correction.corrected_prompt,
                correction.reason,
            )
            self._current_versions[task_type] = new_version
            correction.applied = True
            correction.effectiveness_delta = 0.1  # 预期效果提升
            
            # 更新修正记录
            self.memory.save(
                "prompts",
                f"correction_{correction.correction_id}.json",
                asdict(correction),
            )
            
            print(f"[PromptEvolver] 已应用修正，新版本: {new_version.version_id}")
    
    def _create_evolved_version(
        self,
        task_type: str,
        parent: PromptVersion,
        new_prompt: str,
        evolution_reason: str,
    ) -> PromptVersion:
        """
        创建进化后的提示词版本
        
        Args:
            task_type: 任务类型
            parent: 父版本
            new_prompt: 新提示词文本
            evolution_reason: 进化原因
            
        Returns:
            新版本对象
        """
        version_id = self._generate_version_id(task_type, new_prompt)
        
        new_version = PromptVersion(
            version_id=version_id,
            task_type=task_type,
            prompt_text=new_prompt,
            created_at=datetime.now().isoformat(),
            effectiveness_score=parent.effectiveness_score * 0.9,  # 初始继承父版本90%
            usage_count=0,
            corrections_applied=parent.corrections_applied + 1,
            parent_version=parent.version_id,
            metadata={
                "evolution_reason": evolution_reason,
                "parent_effectiveness": parent.effectiveness_score,
                "evolution_method": "correction_learning",
            },
        )
        
        # 保存新版本
        self._save_version(task_type, new_version)
        
        # 保存版本历史
        self._save_version_history(task_type, new_version)
        
        return new_version
    
    def _save_version(self, task_type: str, version: PromptVersion):
        """保存当前版本"""
        self.memory.save(
            "prompts",
            f"{task_type}_current.json",
            asdict(version),
        )
    
    def _save_version_history(self, task_type: str, version: PromptVersion):
        """保存版本历史"""
        history_file = f"{task_type}_history.json"
        
        try:
            history = self.memory.load("prompts", history_file)
            if not isinstance(history, list):
                history = []
        except:
            history = []
        
        history.append(asdict(version))
        
        # 限制历史长度
        if len(history) > self.MAX_VERSION_HISTORY:
            history = history[-self.MAX_VERSION_HISTORY:]
        
        self.memory.save("prompts", history_file, history)
    
    def evolve(self, task_type: str, base_prompt: str) -> str:
        """
        进化提示词
        
        基于历史学习，返回优化后的提示词。
        如果没有学习记录，返回基础提示词。
        
        Args:
            task_type: 任务类型
            base_prompt: 基础提示词
            
        Returns:
            优化后的提示词文本
        """
        # 检查是否有当前版本
        current = self._current_versions.get(task_type)
        
        if not current:
            # 首次使用，创建初始版本
            version_id = self._generate_version_id(task_type, base_prompt)
            current = PromptVersion(
                version_id=version_id,
                task_type=task_type,
                prompt_text=base_prompt,
                created_at=datetime.now().isoformat(),
                effectiveness_score=0.5,
                usage_count=1,
                metadata={"source": "base_prompt_initialization"},
            )
            self._current_versions[task_type] = current
            self._save_version(task_type, current)
            return base_prompt
        
        # 增加使用计数
        current.usage_count += 1
        self._save_version(task_type, current)
        
        # 检查效果评分，决定是否需要进化
        if current.effectiveness_score < self.EVOLUTION_THRESHOLD:
            # 尝试从修正历史中学习优化
            evolved = self._try_evolve_from_corrections(task_type, current)
            if evolved:
                return evolved.prompt_text
        
        # 返回当前最佳提示词
        return current.prompt_text
    
    def _try_evolve_from_corrections(
        self, task_type: str, current: PromptVersion
    ) -> Optional[PromptVersion]:
        """
        尝试从修正记录中进化提示词
        
        查找该任务类型的修正记录，提取改进模式。
        """
        try:
            all_prompts = self.memory.load_all_prompts()
            corrections = []
            
            for data in all_prompts:
                # 通过 correction_id 字段判断是否为修正记录
                if isinstance(data, dict) and "correction_id" in data and data.get("task_type") == task_type:
                    corrections.append(data)
            
            if not corrections:
                return None
            
            # 按时间排序，取最近的修正
            corrections.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            recent_corrections = corrections[:5]
            
            # 分析修正模式，尝试生成优化提示词
            # 简化策略：如果有高效果修正，采用其修正后版本
            best_correction = None
            best_score = -1
            
            for corr in recent_corrections:
                score = corr.get("effectiveness_delta", 0)
                if score > best_score:
                    best_score = score
                    best_correction = corr
            
            if best_correction and best_score > 0:
                corrected = best_correction.get("corrected_prompt", "")
                if corrected and corrected != current.prompt_text:
                    new_version = self._create_evolved_version(
                        task_type,
                        current,
                        corrected,
                        f"auto_evolve_from_correction:{best_correction.get('correction_id')}",
                    )
                    self._current_versions[task_type] = new_version
                    print(f"[PromptEvolver] 自动进化: {current.version_id} -> {new_version.version_id}")
                    return new_version
            
            return None
        except Exception as e:
            print(f"[PromptEvolver] 进化失败: {e}")
            return None
    
    def update_effectiveness(self, task_type: str, score: float):
        """
        更新提示词效果评分
        
        Args:
            task_type: 任务类型
            score: 新的效果评分 (0.0-1.0)
        """
        current = self._current_versions.get(task_type)
        if not current:
            return
        
        # 滚动加权更新
        current.effectiveness_score = (
            current.effectiveness_score * 0.7 + score * 0.3
        )
        
        self._save_version(task_type, current)
        print(f"[PromptEvolver] 更新效果评分: {task_type} = {current.effectiveness_score:.3f}")
    
    def get_prompt_stats(self, task_type: Optional[str] = None) -> Dict[str, Any]:
        """
        获取提示词统计信息
        
        Args:
            task_type: 指定任务类型，None则返回全部
            
        Returns:
            统计信息字典
        """
        if task_type:
            current = self._current_versions.get(task_type)
            if not current:
                return {}
            return {
                "task_type": task_type,
                "version_id": current.version_id,
                "effectiveness_score": current.effectiveness_score,
                "usage_count": current.usage_count,
                "corrections_applied": current.corrections_applied,
                "created_at": current.created_at,
            }
        
        return {
            task: self.get_prompt_stats(task)
            for task in self._current_versions.keys()
        }
    
    def get_version_history(self, task_type: str) -> List[Dict[str, Any]]:
        """
        获取提示词版本历史
        
        Args:
            task_type: 任务类型
            
        Returns:
            版本历史列表
        """
        try:
            history = self.memory.load("prompts", f"{task_type}_history.json")
            if isinstance(history, list):
                return history
            return []
        except:
            return []
    
    def rollback(self, task_type: str, version_id: str) -> bool:
        """
        回滚到指定版本
        
        Args:
            task_type: 任务类型
            version_id: 目标版本ID
            
        Returns:
            是否成功回滚
        """
        history = self.get_version_history(task_type)
        
        for version_data in history:
            if version_data.get("version_id") == version_id:
                version = self._dict_to_version(version_data)
                self._current_versions[task_type] = version
                self._save_version(task_type, version)
                print(f"[PromptEvolver] 回滚到版本: {version_id}")
                return True
        
        return False
    
    def reset_task(self, task_type: str):
        """
        重置任务类型的提示词
        
        删除所有相关记录，下次 evolve 将重新初始化。
        
        Args:
            task_type: 任务类型
        """
        if task_type in self._current_versions:
            del self._current_versions[task_type]
        
        # 删除相关文件
        for filename in [
            f"{task_type}_current.json",
            f"{task_type}_history.json",
        ]:
            try:
                self.memory.delete("prompts", filename)
            except:
                pass
        
        print(f"[PromptEvolver] 重置任务: {task_type}")
