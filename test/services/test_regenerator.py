"""
VideoRegenerator 单元测试 — FFmpeg 路径查找 + 两阶段合成 + 完整再生成流程

测试范围：
  _find_ffmpeg
    - IMAGEIO_FFMPEG_EXE 环境变量（最高优先级）
    - FFMPEG_PATH 环境变量
    - settings.FFMPEG_PATH（非默认值）
    - shutil.which 系统 PATH
    - imageio_ffmpeg 打包版本（兜底）
    - 全部失败 → RuntimeError

  _combine_video_audio
    - 两阶段全部成功 → True
    - 阶段1失败（returncode≠0）→ False
    - 阶段2失败 → False
    - 正确传递 -an -c:v copy（阶段1）
    - 正确传递 -c:a aac -shortest（阶段2）

  _generate_tts
    - TTS 成功 → 返回音频路径
    - TTS 返回 False → 返回 None
    - TTS 成功但文件不存在 → 返回 None

  regenerate_from_plan
    - 有 script_optimization → TTS + 合成
    - TTS 失败（返回 None）→ 直接复制原文件
    - 无 script_optimization → 直接复制原文件
    - 合成时异常 → 抛出 RuntimeError

  generate_variants
    - 按 creative_variants 数量循环
    - num_variants 超出范围时不越界

  apply_platform_template
    - 模板文件不存在 → 复制原文件
    - 模板文件存在，FFmpeg 执行成功 → 返回 output_path
    - FFmpeg 执行失败 → 回退复制原文件
"""

import json
import os
import shutil
from unittest.mock import MagicMock, call, patch, ANY

import pytest


# ─── 让 VideoRegenerator.__init__ 不真正调用 _find_ffmpeg ─────────────────────

FAKE_FFMPEG = "/fake/ffmpeg"


@pytest.fixture(autouse=True)
def _patch_dependencies(mock_settings, tmp_path):
    """
    全局 patch：
      - get_settings → mock_settings（避免读 .env）
      - shutil.which("ffmpeg") → FAKE_FFMPEG
    """
    mock_settings.FFMPEG_PATH = ""       # 不走 config 路径分支
    mock_settings.TEMP_DIR = str(tmp_path)
    with patch("app.config.get_settings", return_value=mock_settings), \
         patch("shutil.which", return_value=FAKE_FFMPEG):
        yield


@pytest.fixture
def regenerator(tmp_path):
    """构造 VideoRegenerator 实例，FFmpeg 路径已 mock。"""
    with patch("app.services.regenerator.regenerate_video._find_ffmpeg", return_value=FAKE_FFMPEG):
        from app.services.regenerator.regenerate_video import VideoRegenerator
        r = VideoRegenerator()
    r.temp_dir = str(tmp_path)
    return r


# ═══════════════════════════════════════════════════════════════════════════════
# Section 1 — _find_ffmpeg
# ═══════════════════════════════════════════════════════════════════════════════

class TestFindFFmpeg:

    def _call(self, env=None, which_result=None, settings_path="",
              imageio_path=None, file_exists_paths=None):
        from app.services.regenerator.regenerate_video import _find_ffmpeg

        def fake_isfile(path):
            return path in (file_exists_paths or [])

        with patch.dict("os.environ", env or {}, clear=False), \
             patch("os.path.isfile", side_effect=fake_isfile), \
             patch("shutil.which", return_value=which_result):

            mock_settings = MagicMock()
            mock_settings.FFMPEG_PATH = settings_path

            if imageio_path:
                mock_imageio = MagicMock()
                mock_imageio.get_ffmpeg_exe.return_value = imageio_path
                modules = {"imageio_ffmpeg": mock_imageio}
            else:
                modules = {"imageio_ffmpeg": None}  # ImportError 分支

            with patch("app.config.get_settings", return_value=mock_settings):
                with patch.dict("sys.modules", modules):
                    return _find_ffmpeg()

    def test_imageio_ffmpeg_env_var(self, tmp_path):
        fake = str(tmp_path / "ffmpeg_imageio")
        fake_path = fake
        result = self._call(
            env={"IMAGEIO_FFMPEG_EXE": fake_path},
            file_exists_paths=[fake_path],
        )
        assert result == fake_path

    def test_ffmpeg_path_env_var(self, tmp_path):
        fake = str(tmp_path / "ffmpeg_env")
        result = self._call(
            env={"FFMPEG_PATH": fake},
            file_exists_paths=[fake],
        )
        assert result == fake

    def test_imageio_env_takes_priority_over_ffmpeg_env(self, tmp_path):
        imageio_path = str(tmp_path / "imageio_ffmpeg")
        ffmpeg_path = str(tmp_path / "ffmpeg_env")
        result = self._call(
            env={"IMAGEIO_FFMPEG_EXE": imageio_path, "FFMPEG_PATH": ffmpeg_path},
            file_exists_paths=[imageio_path, ffmpeg_path],
        )
        assert result == imageio_path

    def test_settings_configured_path(self, tmp_path):
        custom = str(tmp_path / "custom_ffmpeg")
        result = self._call(
            settings_path=custom,
            file_exists_paths=[custom],
            which_result=None,
        )
        assert result == custom

    def test_settings_default_value_skipped(self):
        """settings.FFMPEG_PATH == '/usr/bin/ffmpeg'（默认值）不作为 settings 路径使用。"""
        with patch("shutil.which", return_value="/usr/bin/ffmpeg") as mock_which:
            with patch("app.config.get_settings", return_value=MagicMock(FFMPEG_PATH="/usr/bin/ffmpeg")):
                with patch("os.path.isfile", return_value=False):
                    from app.services.regenerator.regenerate_video import _find_ffmpeg
                    result = _find_ffmpeg()
        assert result == "/usr/bin/ffmpeg"
        mock_which.assert_called()

    def test_shutil_which_fallback(self):
        with patch("shutil.which", return_value="/opt/bin/ffmpeg"):
            with patch("app.config.get_settings", return_value=MagicMock(FFMPEG_PATH="")):
                with patch("os.path.isfile", return_value=False):
                    from app.services.regenerator.regenerate_video import _find_ffmpeg
                    result = _find_ffmpeg()
        assert result == "/opt/bin/ffmpeg"

    def test_imageio_ffmpeg_package_fallback(self):
        mock_imageio = MagicMock()
        mock_imageio.get_ffmpeg_exe.return_value = "/imageio/ffmpeg"
        with patch("shutil.which", return_value=None):
            with patch("app.config.get_settings", return_value=MagicMock(FFMPEG_PATH="")):
                with patch("os.path.isfile", return_value=False):
                    with patch.dict("sys.modules", {"imageio_ffmpeg": mock_imageio}):
                        from app.services.regenerator import regenerate_video
                        import importlib; importlib.reload(regenerate_video)
                        result = regenerate_video._find_ffmpeg()
        assert result == "/imageio/ffmpeg"

    def test_all_fail_raises_runtime_error(self):
        with patch("shutil.which", return_value=None):
            with patch("app.config.get_settings", return_value=MagicMock(FFMPEG_PATH="")):
                with patch("os.path.isfile", return_value=False):
                    with patch.dict("sys.modules", {"imageio_ffmpeg": None}):
                        from app.services.regenerator import regenerate_video
                        import importlib; importlib.reload(regenerate_video)
                        with pytest.raises(RuntimeError, match="FFmpeg"):
                            regenerate_video._find_ffmpeg()


# ═══════════════════════════════════════════════════════════════════════════════
# Section 2 — _combine_video_audio
# ═══════════════════════════════════════════════════════════════════════════════

class TestCombineVideoAudio:

    def _make_run_result(self, returncode=0, stderr=""):
        r = MagicMock()
        r.returncode = returncode
        r.stderr = stderr
        return r

    def test_both_stages_success(self, regenerator, tmp_video, tmp_audio, output_path):
        ok = self._make_run_result(0)
        with patch("subprocess.run", return_value=ok):
            result = regenerator._combine_video_audio(tmp_video, tmp_audio, output_path)
        assert result is True

    def test_stage1_fail_returns_false(self, regenerator, tmp_video, tmp_audio, output_path):
        fail = self._make_run_result(1, "stage1 error")
        ok = self._make_run_result(0)
        with patch("subprocess.run", side_effect=[fail, ok]):
            result = regenerator._combine_video_audio(tmp_video, tmp_audio, output_path)
        assert result is False

    def test_stage2_fail_returns_false(self, regenerator, tmp_video, tmp_audio, output_path):
        ok = self._make_run_result(0)
        fail = self._make_run_result(1, "stage2 error")
        with patch("subprocess.run", side_effect=[ok, fail]):
            result = regenerator._combine_video_audio(tmp_video, tmp_audio, output_path)
        assert result is False

    def test_stage1_strips_audio_stream(self, regenerator, tmp_video, tmp_audio, output_path):
        """阶段1命令必须包含 -an（去除音频）和 -c:v copy（不重编码）。"""
        ok = self._make_run_result(0)
        calls_captured = []
        with patch("subprocess.run", side_effect=lambda cmd, **kw: (calls_captured.append(cmd), ok)[1]):
            regenerator._combine_video_audio(tmp_video, tmp_audio, output_path)
        stage1_cmd = calls_captured[0]
        assert "-an" in stage1_cmd
        assert "-c:v" in stage1_cmd
        assert "copy" in stage1_cmd

    def test_stage2_uses_aac_and_shortest(self, regenerator, tmp_video, tmp_audio, output_path):
        """阶段2命令必须包含 -c:a aac 和 -shortest。"""
        ok = self._make_run_result(0)
        calls_captured = []
        with patch("subprocess.run", side_effect=lambda cmd, **kw: (calls_captured.append(cmd), ok)[1]):
            regenerator._combine_video_audio(tmp_video, tmp_audio, output_path)
        stage2_cmd = calls_captured[1]
        assert "-c:a" in stage2_cmd
        assert "aac" in stage2_cmd
        assert "-shortest" in stage2_cmd

    def test_stage2_receives_audio_path(self, regenerator, tmp_video, tmp_audio, output_path):
        """阶段2命令中应包含传入的 audio_path。"""
        ok = self._make_run_result(0)
        calls_captured = []
        with patch("subprocess.run", side_effect=lambda cmd, **kw: (calls_captured.append(cmd), ok)[1]):
            regenerator._combine_video_audio(tmp_video, tmp_audio, output_path)
        assert tmp_audio in calls_captured[1]

    def test_stage2_output_path_is_final(self, regenerator, tmp_video, tmp_audio, output_path):
        """阶段2的最终输出路径应为传入的 output_path。"""
        ok = self._make_run_result(0)
        calls_captured = []
        with patch("subprocess.run", side_effect=lambda cmd, **kw: (calls_captured.append(cmd), ok)[1]):
            regenerator._combine_video_audio(tmp_video, tmp_audio, output_path)
        assert output_path in calls_captured[1]

    def test_subprocess_called_exactly_twice(self, regenerator, tmp_video, tmp_audio, output_path):
        ok = self._make_run_result(0)
        with patch("subprocess.run", return_value=ok) as mock_run:
            regenerator._combine_video_audio(tmp_video, tmp_audio, output_path)
        assert mock_run.call_count == 2


# ═══════════════════════════════════════════════════════════════════════════════
# Section 3 — _generate_tts
# ═══════════════════════════════════════════════════════════════════════════════

class TestGenerateTTS:

    def test_success_returns_audio_path(self, regenerator, tmp_path):
        audio_file = str(tmp_path / "tts_output.mp3")

        def fake_tts(text, voice_name, output_file, voice_rate, voice_volume):
            open(output_file, "wb").write(b"\xff\xfb\x90\x00" + b"\x00" * 64)
            return True

        with patch("app.services.regenerator.regenerate_video.run_tts", side_effect=fake_tts):
            result = regenerator._generate_tts("你好世界，这是一段测试文案。")

        assert result is not None
        assert result.endswith(".mp3")
        assert os.path.exists(result)

    def test_tts_returns_false_returns_none(self, regenerator):
        with patch("app.services.regenerator.regenerate_video.run_tts", return_value=False):
            result = regenerator._generate_tts("text")
        assert result is None

    def test_tts_success_but_no_file_returns_none(self, regenerator):
        """run_tts 返回 True 但文件未创建 → _generate_tts 应返回 None。"""
        with patch("app.services.regenerator.regenerate_video.run_tts", return_value=True):
            result = regenerator._generate_tts("text")
        assert result is None

    def test_voice_name_passed_from_settings(self, regenerator, mock_settings, tmp_path):
        mock_settings.TTS_VOICE_NAME = "siliconflow:bella"
        mock_settings.TTS_VOICE_RATE = 5
        mock_settings.TTS_VOICE_VOLUME = 1.2
        captured = {}

        def fake_tts(text, voice_name, output_file, voice_rate, voice_volume):
            captured.update({"voice_name": voice_name, "rate": voice_rate, "volume": voice_volume})
            open(output_file, "wb").write(b"\x00" * 10)
            return True

        with patch("app.services.regenerator.regenerate_video.run_tts", side_effect=fake_tts):
            with patch("app.config.get_settings", return_value=mock_settings):
                from app.services.regenerator import regenerate_video
                import importlib; importlib.reload(regenerate_video)
                with patch("app.services.regenerator.regenerate_video._find_ffmpeg", return_value=FAKE_FFMPEG):
                    r = regenerate_video.VideoRegenerator()
                    r.temp_dir = str(tmp_path)
                    r._generate_tts("text")

        assert captured["voice_name"] == "siliconflow:bella"
        assert captured["rate"] == 5
        assert abs(captured["volume"] - 1.2) < 1e-9


# ═══════════════════════════════════════════════════════════════════════════════
# Section 4 — regenerate_from_plan
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegenerateFromPlan:

    def test_with_script_calls_tts_and_combine(
        self, regenerator, tmp_video, tmp_audio, output_path,
        optimization_plan_with_script,
    ):
        regenerator._generate_tts = MagicMock(return_value=tmp_audio)
        regenerator._combine_video_audio = MagicMock(return_value=True)

        result = regenerator.regenerate_from_plan(
            tmp_video, optimization_plan_with_script, output_path=output_path
        )

        regenerator._generate_tts.assert_called_once()
        regenerator._combine_video_audio.assert_called_once_with(tmp_video, tmp_audio, output_path)
        assert result == output_path

    def test_without_script_copies_original(
        self, regenerator, tmp_video, output_path,
        optimization_plan_no_script,
    ):
        regenerator._generate_tts = MagicMock()
        with patch("shutil.copy2") as mock_copy:
            result = regenerator.regenerate_from_plan(
                tmp_video, optimization_plan_no_script, output_path=output_path
            )
        mock_copy.assert_called_once_with(tmp_video, output_path)
        regenerator._generate_tts.assert_not_called()

    def test_tts_failure_copies_original(
        self, regenerator, tmp_video, output_path,
        optimization_plan_with_script,
    ):
        regenerator._generate_tts = MagicMock(return_value=None)
        with patch("shutil.copy2") as mock_copy:
            result = regenerator.regenerate_from_plan(
                tmp_video, optimization_plan_with_script, output_path=output_path
            )
        mock_copy.assert_called_once_with(tmp_video, output_path)

    def test_auto_output_path_generation(
        self, regenerator, tmp_video,
        optimization_plan_no_script,
    ):
        """不传 output_path 时，应自动生成 <base>_optimized_<variant_id>.mp4。"""
        with patch("shutil.copy2"):
            result = regenerator.regenerate_from_plan(
                tmp_video, optimization_plan_no_script, variant_id="v99"
            )
        assert "optimized_v99" in result
        assert result.endswith(".mp4")

    def test_exception_in_combine_raises_runtime_error(
        self, regenerator, tmp_video, tmp_audio, output_path,
        optimization_plan_with_script,
    ):
        regenerator._generate_tts = MagicMock(return_value=tmp_audio)
        regenerator._combine_video_audio = MagicMock(side_effect=OSError("disk full"))

        with pytest.raises(RuntimeError, match="视频重生成失败"):
            regenerator.regenerate_from_plan(
                tmp_video, optimization_plan_with_script, output_path=output_path
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Section 5 — generate_variants
# ═══════════════════════════════════════════════════════════════════════════════

class TestGenerateVariants:

    def test_generates_correct_number_of_variants(
        self, regenerator, tmp_video,
        optimization_plan_with_script,
    ):
        regenerator.regenerate_from_plan = MagicMock(side_effect=lambda **kw: kw["output_path"])

        with patch.object(regenerator, "regenerate_from_plan",
                          side_effect=lambda **kw: "/fake/" + kw.get("variant_id", "v1") + ".mp4"):
            results = regenerator.generate_variants(tmp_video, optimization_plan_with_script, num_variants=2)

        assert len(results) == 2

    def test_num_variants_capped_at_plan_length(
        self, regenerator, tmp_video,
        optimization_plan_with_script,
    ):
        """num_variants=10 但 plan 只有 2 个变体 → 只生成 2 个。"""
        calls = []
        original_fn = regenerator.regenerate_from_plan

        def capture(*args, **kwargs):
            calls.append(kwargs.get("variant_id", ""))
            with patch("shutil.copy2"):
                return original_fn(*args, **kwargs)

        regenerator.regenerate_from_plan = capture
        with patch("shutil.copy2"):
            results = regenerator.generate_variants(tmp_video, optimization_plan_with_script, num_variants=10)
        assert len(results) == 2

    def test_zero_variants_in_plan(
        self, regenerator, tmp_video,
    ):
        from app.models.schema import OptimizationPlan
        empty_plan = OptimizationPlan(analysis_id="x", creative_variants=[])
        results = regenerator.generate_variants(tmp_video, empty_plan, num_variants=3)
        assert results == []


# ═══════════════════════════════════════════════════════════════════════════════
# Section 6 — apply_platform_template
# ═══════════════════════════════════════════════════════════════════════════════

class TestApplyPlatformTemplate:

    def test_missing_template_copies_original(self, regenerator, tmp_video, output_path):
        with patch("os.path.exists", return_value=False):
            with patch("shutil.copy2") as mock_copy:
                result = regenerator.apply_platform_template(tmp_video, "douyin", output_path)
        mock_copy.assert_called_once_with(tmp_video, output_path)
        assert result == output_path

    def test_template_exists_calls_ffmpeg_scale(self, regenerator, tmp_video, tmp_path, output_path):
        template = {"optimal_specs": {"resolution": "1080x1920"}}
        template_file = str(tmp_path / "douyin_template.json")
        with open(template_file, "w") as f:
            json.dump(template, f)

        ok = MagicMock(returncode=0, stderr="")
        ffmpeg_cmd = []
        with patch("os.path.exists", return_value=True), \
             patch("builtins.open", side_effect=lambda path, *a, **k:
                   open(template_file, *a, **k) if "template" in path else open(path, *a, **k)), \
             patch("subprocess.run", return_value=ok) as mock_run:
            regenerator.apply_platform_template(tmp_video, "douyin", output_path)

        cmd = mock_run.call_args[0][0]
        assert "scale=1080:1920" in " ".join(cmd)

    def test_ffmpeg_fail_falls_back_to_copy(self, regenerator, tmp_video, tmp_path, output_path):
        template = {"optimal_specs": {"resolution": "1920x1080"}}
        template_file = str(tmp_path / "youtube_template.json")
        with open(template_file, "w") as f:
            json.dump(template, f)

        fail = MagicMock(returncode=1, stderr="ffmpeg error")
        with patch("os.path.exists", return_value=True), \
             patch("builtins.open", side_effect=lambda path, *a, **k:
                   open(template_file, *a, **k) if "template" in path else open(path, *a, **k)), \
             patch("subprocess.run", return_value=fail), \
             patch("shutil.copy2") as mock_copy:
            result = regenerator.apply_platform_template(tmp_video, "youtube", output_path)

        mock_copy.assert_called_once_with(tmp_video, output_path)
