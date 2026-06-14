"""
视频元数据解析器
"""

import cv2
import subprocess
import json
import os
import tempfile
from typing import List, Optional
from app.models.schema import VideoMetadata
from app.config import get_settings
from app.utils.logger import logger

settings = get_settings()

class VideoParser:
    """视频元数据解析器"""
    
    @staticmethod
    def parse_video(video_path: str) -> VideoMetadata:
        """
        提取视频元数据

        Args:
            video_path: 视频文件路径

        Returns:
            VideoMetadata: 视频元数据对象
        """
        cap = None
        try:
            cap = cv2.VideoCapture(video_path)

            if not cap.isOpened():
                raise ValueError(f"无法打开视频文件: {video_path}")

            fps = int(cap.get(cv2.CAP_PROP_FPS))
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        finally:
            if cap is not None:
                cap.release()

        # 使用 ffprobe 获取详细元数据
        ffprobe_path = VideoParser._get_ffprobe_path()
        bitrate, format_name = VideoParser._get_ffprobe_info(video_path, ffprobe_path)

        return VideoMetadata(
            duration=duration,
            fps=fps,
            resolution=f"{width}x{height}",
            bitrate=bitrate,
            format=format_name,
            file_size=VideoParser._get_file_size(video_path)
        )
    
    @staticmethod
    def _get_ffprobe_path() -> str:
        """获取 ffprobe 路径，基于 ffmpeg 路径"""
        ffmpeg_path = settings.FFMPEG_PATH
        base_dir = os.path.dirname(ffmpeg_path)
        # 假设 ffprobe 与 ffmpeg 在同一目录，且名称为 ffprobe
        return os.path.join(base_dir, "ffprobe")

    @staticmethod
    def _get_ffprobe_info(video_path: str, ffprobe_path: str = None) -> tuple:
        """使用 ffprobe 获取比特率和格式"""
        if ffprobe_path is None:
            ffmpeg_path = settings.FFMPEG_PATH
            base_dir = os.path.dirname(ffmpeg_path)
            ffprobe_path = os.path.join(base_dir, "ffprobe")

        try:
            cmd = [
                ffprobe_path,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                video_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                info = json.loads(result.stdout)
                bitrate = int(info.get('format', {}).get('bit_rate', 0))
                format_name = info.get('format', {}).get('format_name', 'unknown')
                return bitrate, format_name
        except Exception as e:
            logger.warning(f"ffprobe 获取信息失败: {e}")

        return 0, 'unknown'
    
    @staticmethod
    def _get_file_size(video_path: str) -> Optional[int]:
        """获取文件大小"""
        try:
            return os.path.getsize(video_path)
        except OSError:
            return None
    
    @staticmethod
    def extract_frames(
        video_path: str,
        interval: int = 1,
        max_frames: int = 10
    ) -> List[str]:
        """
        按间隔提取关键帧
        
        Args:
            video_path: 视频文件路径
            interval: 提取间隔（秒）
            max_frames: 最大帧数
            
        Returns:
            List[str]: 提取的帧图像路径列表
        """
        frames = []
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise ValueError(f"无法打开视频文件: {video_path}")

        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            interval_frames = int(fps * interval)
            frame_count = 0
            saved_count = 0

            while True:
                ret, frame = cap.read()
                if not ret or saved_count >= max_frames:
                    break

                if frame_count % interval_frames == 0:
                    fd, temp_path = tempfile.mkstemp(suffix='.jpg')
                    os.close(fd)
                    cv2.imwrite(temp_path, frame)
                    frames.append(temp_path)
                    saved_count += 1

                frame_count += 1
        finally:
            cap.release()

        return frames
    
    @staticmethod
    def get_video_info_summary(video_path: str) -> str:
        """
        获取视频信息摘要（用于 Prompt）
        
        Returns:
            str: 格式化的视频信息字符串
        """
        try:
            metadata = VideoParser.parse_video(video_path)
            return f""" 
- 分辨率: {metadata.resolution}
- 时长: {metadata.duration:.1f}秒
- 帧率: {metadata.fps}
- 比特率: {metadata.bitrate}
- 格式: {metadata.format}
"""
        except Exception as e:
            return f"获取视频信息失败: {str(e)}"
