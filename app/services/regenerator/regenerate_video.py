"""
视频重生成模块
"""

import os
import subprocess
from typing import List, Dict, Optional
from app.config import get_settings
from app.models.schema import VideoAnalysisResult, OptimizationPlan
from app.utils.logger import logger

settings = get_settings()

class VideoRegenerator:
    """基于优化方案重新生成视频"""
    
    def __init__(self):
        self.ffmpeg_path = settings.FFMPEG_PATH
        self.temp_dir = settings.TEMP_DIR
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def regenerate_from_plan(
        self,
        original_video_path: str,
        optimization_plan: OptimizationPlan,
        variant_id: str = "v1",
        output_path: Optional[str] = None
    ) -> str:
        """
        基于优化方案重新生成视频
        
        Args:
            original_video_path: 原视频路径
            optimization_plan: 优化方案
            variant_id: 版本 ID
            output_path: 输出路径（可选）
            
        Returns:
            str: 新视频路径
        """
        if not output_path:
            base_name = os.path.splitext(original_video_path)[0]
            output_path = f"{base_name}_optimized_{variant_id}.mp4"
        
        try:
            # 1. 提取音频并重新生成配音（如果有优化文案）
            new_audio_path = None
            if optimization_plan.script_optimization:
                new_script = optimization_plan.script_optimization.optimized_script
                new_audio_path = self._generate_tts(new_script)
            
            # 2. 提取原视频画面
            frames_dir = self._extract_frames(original_video_path)
            
            # 3. 重新合成视频
            if new_audio_path:
                self._combine_video_audio(
                    frames_dir,
                    new_audio_path,
                    output_path
                )
            else:
                # 如果没有新音频，直接复制原视频
                import shutil
                shutil.copy2(original_video_path, output_path)
            
            # 4. 应用平台适配（如果需要）
            # TODO: 根据平台调整分辨率、添加字幕等
            
            return output_path
            
        except Exception as e:
            raise RuntimeError(f"视频重生成失败: {str(e)}")
    
    def generate_variants(
        self,
        original_video_path: str,
        plan: OptimizationPlan,
        num_variants: int = 3
    ) -> List[str]:
        """
        生成多个版本
        
        Returns:
            List[str]: 生成的视频路径列表
        """
        results = []
        
        for i in range(min(num_variants, len(plan.creative_variants))):
            variant = plan.creative_variants[i]
            output_path = self.regenerate_from_plan(
                original_video_path=original_video_path,
                optimization_plan=plan,
                variant_id=variant.variant_id
            )
            results.append(output_path)
        
        return results
    
    def apply_platform_template(
        self,
        video_path: str,
        platform: str,
        output_path: Optional[str] = None
    ) -> str:
        """
        应用平台模板
        
        Args:
            video_path: 视频路径
            platform: 平台名称 (douyin/xiaohongshu/weixin)
            output_path: 输出路径
            
        Returns:
            str: 应用模板后的视频路径
        """
        if not output_path:
            base_name = os.path.splitext(video_path)[0]
            output_path = f"{base_name}_{platform}.mp4"
        
        # 读取平台配置
        template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "resource", "templates", f"{platform}_template.json")
        
        if not os.path.exists(template_path):
            # 没有模板，直接返回原视频
            import shutil
            shutil.copy2(video_path, output_path)
            return output_path
        
        try:
            import json
            with open(template_path, 'r', encoding='utf-8') as f:
                template = json.load(f)
            
            # 获取目标分辨率
            target_resolution = template.get("optimal_specs", {}).get("resolution", "1920x1080")
            width, height = map(int, target_resolution.split('x'))
            
            # 使用 ffmpeg 调整分辨率
            cmd = [
                self.ffmpeg_path,
                '-i', video_path,
                '-vf', f'scale={width}:{height}',
                '-c:a', 'copy',
                output_path,
                '-y'  # 覆盖输出文件
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg 失败: {result.stderr}")
            
            return output_path
            
        except Exception as e:
            logger.warning(f"应用平台模板失败: {e}")
            # 失败时返回原视频
            import shutil
            shutil.copy2(video_path, output_path)
            return output_path
    
    def _generate_tts(self, text: str) -> Optional[str]:
        """
        生成 TTS 音频（简化版 - 实际应用中应使用 TTS 服务）
        
        Returns:
            str: 音频文件路径，失败返回 None
        """
        # TODO: 集成 TTS 服务（如 Azure、讯飞、阿里云等）
        # 这里返回一个占位符
        logger.info(f"TTS 生成（待实现）: {text[:50]}...")
        return None
    
    def _extract_frames(self, video_path: str) -> str:
        """
        提取视频帧到临时目录
        
        Returns:
            str: 帧目录路径
        """
        frames_dir = os.path.join(self.temp_dir, "frames")
        os.makedirs(frames_dir, exist_ok=True)
        
        cmd = [
            self.ffmpeg_path,
            '-y',
            '-i', video_path,
            '-vf', 'fps=1',  # 每秒提取一帧（示例）
            os.path.join(frames_dir, 'frame_%04d.jpg')
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, timeout=60)
        except Exception as e:
            logger.warning(f"提取帧失败: {e}")
        
        return frames_dir
    
    def _combine_video_audio(
        self,
        frames_dir: str,
        audio_path: str,
        output_path: str
    ) -> bool:
        """
        将帧和音频合成为视频
        
        Returns:
            bool: 是否成功
        """
        # TODO: 实现帧到视频的合成
        # 这需要使用 ffmpeg 或 OpenCV 的视频编写器
        logger.info("视频合成（待实现）")
        return False
