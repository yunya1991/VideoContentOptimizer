"""
共享 pytest fixtures — TTS / Regenerator / 压力测试
所有测试不依赖真实 FFmpeg / TTS API / 外部网络。
"""

import os
import pytest
from unittest.mock import MagicMock, patch


# ─── 文件 fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_video(tmp_path):
    """最小合法 MP4（ftyp box 头 + 零填充），足够触发文件存在判断。"""
    f = tmp_path / "sample.mp4"
    f.write_bytes(b"\x00\x00\x00\x20ftypisom\x00\x00\x00\x00isomiso2" + b"\x00" * 256)
    return str(f)


@pytest.fixture
def tmp_audio(tmp_path):
    """最小 MP3（同步字 0xfffb + 帧数据），用于音频文件存在性校验。"""
    f = tmp_path / "audio.mp3"
    f.write_bytes(b"\xff\xfb\x90\x00" + b"\x00" * 128)
    return str(f)


@pytest.fixture
def output_path(tmp_path):
    return str(tmp_path / "output.mp4")


# ─── TTS 相关 fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def mock_edge_tts_success(tmp_path):
    """
    patch edge_tts.Communicate.save，写入最小 MP3 后正常返回。
    用于 _edge_tts 成功路径测试。
    """
    import asyncio

    async def fake_save(path):
        with open(path, "wb") as f:
            f.write(b"\xff\xfb\x90\x00" + b"\x00" * 64)

    mock_communicate = MagicMock()
    mock_communicate.save = fake_save

    mock_module = MagicMock()
    mock_module.Communicate.return_value = mock_communicate

    with patch.dict("sys.modules", {"edge_tts": mock_module}):
        yield mock_module


@pytest.fixture
def mock_requests_post():
    """patch requests.post，返回 200 + 伪 MP3 内容。"""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.content = b"\xff\xfb\x90\x00" + b"\x00" * 64
    with patch("requests.post", return_value=mock_resp) as m:
        yield m


@pytest.fixture
def mock_subprocess_ok():
    """subprocess.run 始终返回 returncode=0。"""
    result = MagicMock()
    result.returncode = 0
    result.stderr = ""
    with patch("subprocess.run", return_value=result) as m:
        yield m


@pytest.fixture
def mock_ffmpeg_which():
    """shutil.which('ffmpeg') 返回固定路径。"""
    with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
        yield "/usr/bin/ffmpeg"


# ─── Schema fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def optimization_plan_with_script():
    from app.models.schema import OptimizationPlan, ScriptOptimization, CreativeVariant
    return OptimizationPlan(
        analysis_id="test-001",
        script_optimization=ScriptOptimization(
            original_script="这是原始视频文案内容",
            optimized_script="优化后的爆款文案，吸引更多用户点击观看！",
            optimization_reasons=["增强钩子", "情绪共鸣"],
        ),
        creative_variants=[
            CreativeVariant(variant_id="v1", hook_type="question", description="提问式开头"),
            CreativeVariant(variant_id="v2", hook_type="story", description="故事式开头"),
        ],
    )


@pytest.fixture
def optimization_plan_no_script():
    from app.models.schema import OptimizationPlan, CreativeVariant
    return OptimizationPlan(
        analysis_id="test-002",
        script_optimization=None,
        creative_variants=[
            CreativeVariant(variant_id="v1", hook_type="shocking", description="悬念式"),
        ],
    )


# ─── Settings mock ────────────────────────────────────────────────────────────

@pytest.fixture
def mock_settings(tmp_path):
    """最小化 settings，避免触发真实配置文件加载。"""
    s = MagicMock()
    s.TTS_VOICE_NAME = "edge:zh-CN-XiaoxiaoNeural"
    s.TTS_VOICE_RATE = 0
    s.TTS_VOICE_VOLUME = 1.0
    s.AZURE_SPEECH_KEY = ""
    s.AZURE_SPEECH_REGION = "eastus"
    s.SILICONFLOW_API_KEY = ""
    s.GEMINI_API_KEY = ""
    s.MIMO_API_KEY = ""
    s.FFMPEG_PATH = ""
    s.TEMP_DIR = str(tmp_path)
    return s
