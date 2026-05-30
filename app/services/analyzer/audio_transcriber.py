"""
音频转录器（基于 Faster Whisper）
"""

import tempfile
import subprocess
import os
from typing import Optional, List
from app.config import get_settings
from app.models.schema import VideoIntent

settings = get_settings()

class AudioTranscriber:
    """将视频音频转为文本"""
    
    def __init__(self, model_size: Optional[str] = None):
        """
        初始化转录器
        
        Args:
            model_size: 模型大小 (tiny, base, small, medium, large)
        """
        self.model_size = model_size or settings.WHISPER_MODEL_SIZE
        self.device = settings.WHISPER_DEVICE
        self.compute_type = settings.WHISPER_COMPUTE_TYPE
        self._model = None
    
    @property
    def model(self):
        """懒加载模型"""
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
                self._model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type
                )
            except ImportError:
                raise ImportError(
                    "请安装 faster-whisper: pip install faster-whisper"
                )
        return self._model
    
    def transcribe(
        self,
        video_path: str,
        language: Optional[str] = "zh",
        beam_size: int = 5
    ) -> str:
        """
        转录视频音频为文本
        
        Args:
            video_path: 视频文件路径
            language: 语言代码（None 为自动检测）
            beam_size: beam search 大小
            
        Returns:
            str: 转录文本
        """
        # 提取音频
        audio_path = self._extract_audio(video_path)
        
        try:
            # 转录
            segments, info = self.model.transcribe(
                audio_path,
                language=language,
                beam_size=beam_size
            )
            
            # 拼接所有片段
            transcript = " ".join([segment.text for segment in segments])
            
            # 清理临时文件
            self._cleanup_temp_file(audio_path)
            
            return transcript.strip()
        
        except Exception as e:
            self._cleanup_temp_file(audio_path)
            raise RuntimeError(f"转录失败: {str(e)}")
    
    def transcribe_with_timestamps(
        self,
        video_path: str,
        language: Optional[str] = "zh"
    ) -> List[dict]:
        """
        转录并返回时间戳
        
        Returns:
            List[dict]: [{"start": 0.0, "end": 2.5, "text": "..."}, ...]
        """
        audio_path = self._extract_audio(video_path)
        
        try:
            segments, info = self.model.transcribe(
                audio_path,
                language=language
            )
            
            results = [
                {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip()
                }
                for segment in segments
            ]
            
            self._cleanup_temp_file(audio_path)
            return results
        
        except Exception as e:
            self._cleanup_temp_file(audio_path)
            raise RuntimeError(f"转录失败: {str(e)}")
    
    def _extract_audio(self, video_path: str) -> str:
        """提取音频到临时文件"""
        temp_audio = tempfile.mktemp(suffix='.wav')
        
        cmd = [
            settings.FFMPEG_PATH,
            '-i', video_path,
            '-vn',  # 禁用视频
            '-acodec', 'pcm_s16le',  # PCM 编码
            '-ar', '16000',  # 采样率 16kHz
            '-ac', '1',  # 单声道
            temp_audio,
            '-y'  # 覆盖输出文件
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"音频提取失败: {result.stderr}")
            
            return temp_audio
        
        except subprocess.TimeoutExpired:
            raise RuntimeError("音频提取超时（超过5分钟）")
    
    def _cleanup_temp_file(self, file_path: Optional[str]):
        """清理临时文件"""
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass  # 忽略清理失败
