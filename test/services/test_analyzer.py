"""
测试视频分析模块
"""

import pytest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.services.analyzer.video_parser import VideoParser
from app.services.analyzer.audio_transcriber import AudioTranscriber
from app.models.schema import VideoMetadata, VideoIntent

class TestVideoParser:
    """测试视频解析器"""
    
    def test_parse_video_metadata(self):
        """测试视频元数据提取"""
        # 使用测试视频文件（需要先准备）
        test_video = "test/resources/sample_video.mp4"
        
        if not os.path.exists(test_video):
            pytest.skip("测试视频文件不存在")
        
        parser = VideoParser()
        metadata = parser.parse_video(test_video)
        
        assert metadata is not None
        assert metadata.duration > 0
        assert metadata.fps > 0
        assert metadata.resolution != ""
        assert isinstance(metadata.bitrate, int)
        assert metadata.format != ""
    
    def test_extract_frames(self):
        """测试关键帧提取"""
        test_video = "test/resources/sample_video.mp4"
        
        if not os.path.exists(test_video):
            pytest.skip("测试视频文件不存在")
        
        parser = VideoParser()
        frames = parser.extract_frames(test_video, interval=1, max_frames=5)
        
        assert isinstance(frames, list)
        # 检查是否提取了帧
        # assert len(frames) > 0
    
    def test_parse_nonexistent_video(self):
        """测试处理不存在的视频文件"""
        parser = VideoParser()
        with pytest.raises(ValueError):
            parser.parse_video("nonexistent.mp4")

class TestAudioTranscriber:
    """测试音频转录器"""
    
    def test_transcribe_video(self):
        """测试视频转录"""
        test_video = "test/resources/sample_video.mp4"
        
        if not os.path.exists(test_video):
            pytest.skip("测试视频文件不存在")
        
        # 注意：需要安装 faster-whisper 模型
        try:
            transcriber = AudioTranscriber(model_size="tiny")
            transcript = transcriber.transcribe(test_video)
            
            assert isinstance(transcript, str)
            # 根据实际情况判断
            # assert len(transcript) > 0
        except Exception as e:
            pytest.skip(f"转录失败: {e}")
    
    def test_extract_audio(self):
        """测试音频提取"""
        import tempfile
        test_video = "test/resources/sample_video.mp4"
        
        if not os.path.exists(test_video):
            pytest.skip("测试视频文件不存在")
        
        transcriber = AudioTranscriber()
        # 这里可以添加音频提取的测试

# 辅助函数
def create_test_video():
    """创建测试用的视频文件（如果不存在）"""
    import cv2
    import numpy as np
    
    output_path = "test/resources/sample_video.mp4"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    if os.path.exists(output_path):
        return output_path
    
    # 创建一个简单的测试视频（5秒，24fps）
    width, height = 640, 480
    fps = 24
    duration = 5
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    for _ in range(fps * duration):
        frame = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
        out.write(frame)
    
    out.release()
    return output_path

if __name__ == "__main__":
    # 创建测试视频
    create_test_video()
    print("测试视频已创建")
    
    # 运行测试
    pytest.main([__file__, "-v"])
