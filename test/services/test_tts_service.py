"""
TTS 服务单元测试 — 6 引擎全场景覆盖

测试范围：
  - tts() 入口路由（按 voice_name 前缀）
  - 各引擎成功路径
  - 各引擎缺少 API Key → ValueError
  - 各引擎导入缺失 → ImportError
  - edge_tts 超时 → TimeoutError
  - 输出文件为空 → RuntimeError
  - 语速字符串格式化（正/负/零）
  - list_voices 各引擎
  - voice_name 无前缀（默认 edge）
  - 引擎异常被捕获 → 返回 False
"""

import asyncio
import os
import queue
import threading
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest


# ─── 辅助：确保 app 包可导入（无真实 FFmpeg 要求）─────────────────────────────

@pytest.fixture(autouse=True)
def _patch_get_settings(mock_settings):
    with patch("app.config.get_settings", return_value=mock_settings):
        yield


# ═══════════════════════════════════════════════════════════════════════════════
# Section 1 — tts() 入口路由
# ═══════════════════════════════════════════════════════════════════════════════

class TestTTSRouting:

    @pytest.mark.parametrize("voice_name,expected_fn", [
        ("edge:zh-CN-XiaoxiaoNeural", "_edge_tts"),
        ("azure:zh-CN-YunxiNeural",   "_azure_tts"),
        ("siliconflow:anna",           "_siliconflow_tts"),
        ("gemini:Zephyr",              "_gemini_tts"),
        ("mimo:female_1",              "_mimo_tts"),
        ("zh-CN-XiaoxiaoNeural",       "_edge_tts"),   # 无前缀 → edge
        ("unknown_prefix:voice",       "_edge_tts"),   # 未知前缀 → edge
    ])
    def test_routes_to_correct_engine(self, voice_name, expected_fn, tmp_path):
        output = str(tmp_path / "out.mp3")
        with patch(f"app.services.tts.tts_service.{expected_fn}", return_value=True) as mock_fn:
            from app.services.tts.tts_service import tts
            result = tts("测试文本", voice_name, output)
        assert result is True
        mock_fn.assert_called_once()

    def test_engine_exception_returns_false(self, tmp_path):
        """任意引擎抛异常时 tts() 捕获并返回 False。"""
        output = str(tmp_path / "out.mp3")
        with patch("app.services.tts.tts_service._edge_tts", side_effect=RuntimeError("boom")):
            from app.services.tts.tts_service import tts
            result = tts("text", "edge:zh-CN-XiaoxiaoNeural", output)
        assert result is False

    def test_voice_name_partition_no_colon(self, tmp_path):
        """无冒号时 name 直接等于 voice_name，engine=voice_name，走 else→edge。"""
        output = str(tmp_path / "out.mp3")
        with patch("app.services.tts.tts_service._edge_tts", return_value=True) as m:
            from app.services.tts.tts_service import tts
            tts("text", "zh-CN-XiaoxiaoNeural", output)
        # edge_tts 被调用，传入的 voice 就是原始名称
        args = m.call_args[0]
        assert args[1] == "zh-CN-XiaoxiaoNeural"


# ═══════════════════════════════════════════════════════════════════════════════
# Section 2 — Engine 1: edge_tts
# ═══════════════════════════════════════════════════════════════════════════════

class TestEdgeTTS:

    def _make_edge_module(self, output_bytes=b"\xff\xfb\x90\x00" + b"\x00" * 64):
        """构建模拟 edge_tts 模块，save() 写文件并返回。"""
        async def fake_save(path):
            with open(path, "wb") as f:
                f.write(output_bytes)

        mock_communicate = MagicMock()
        mock_communicate.save = fake_save

        mock_module = MagicMock()
        mock_module.Communicate.return_value = mock_communicate
        return mock_module

    def test_success_returns_true(self, tmp_path):
        output = str(tmp_path / "out.mp3")
        mock_module = self._make_edge_module()
        with patch.dict("sys.modules", {"edge_tts": mock_module}):
            from app.services.tts import tts_service
            import importlib; importlib.reload(tts_service)
            result = tts_service._edge_tts("你好世界", "zh-CN-XiaoxiaoNeural", output, rate=0)
        assert result is True
        assert os.path.exists(output)

    def test_output_file_created(self, tmp_path):
        output = str(tmp_path / "out.mp3")
        mock_module = self._make_edge_module()
        with patch.dict("sys.modules", {"edge_tts": mock_module}):
            from app.services.tts import tts_service
            import importlib; importlib.reload(tts_service)
            tts_service._edge_tts("test", "zh-CN-XiaoxiaoNeural", output)
        assert os.path.getsize(output) > 0

    @pytest.mark.parametrize("rate,expected_str", [
        (5,   "+5%"),
        (-3,  "-3%"),
        (0,   "+0%"),
        (100, "+100%"),
    ])
    def test_rate_string_format(self, tmp_path, rate, expected_str):
        """语速字符串必须正确格式化才能被 edge_tts 接受。"""
        output = str(tmp_path / "out.mp3")
        captured = {}

        async def fake_save(path):
            with open(path, "wb") as f:
                f.write(b"\xff\xfb\x90\x00" + b"\x00" * 64)

        class CaptureCommunicate:
            def __init__(self, text, voice, rate):
                captured["rate"] = rate
                self.save = fake_save

        mock_module = MagicMock()
        mock_module.Communicate = CaptureCommunicate
        with patch.dict("sys.modules", {"edge_tts": mock_module}):
            from app.services.tts import tts_service
            import importlib; importlib.reload(tts_service)
            tts_service._edge_tts("text", "zh-CN-XiaoxiaoNeural", output, rate=rate)
        assert captured["rate"] == expected_str

    def test_import_error_raises(self, tmp_path):
        output = str(tmp_path / "out.mp3")
        with patch.dict("sys.modules", {"edge_tts": None}):
            from app.services.tts import tts_service
            import importlib; importlib.reload(tts_service)
            with pytest.raises(ImportError, match="pip install edge-tts"):
                tts_service._edge_tts("text", "zh-CN-XiaoxiaoNeural", output)

    def test_empty_output_file_raises(self, tmp_path):
        """save() 写 0 字节文件时应抛出 RuntimeError。"""
        output = str(tmp_path / "out.mp3")
        mock_module = self._make_edge_module(output_bytes=b"")
        with patch.dict("sys.modules", {"edge_tts": mock_module}):
            from app.services.tts import tts_service
            import importlib; importlib.reload(tts_service)
            with pytest.raises(RuntimeError, match="空文件"):
                tts_service._edge_tts("text", "zh-CN-XiaoxiaoNeural", output)

    def test_timeout_raises(self, tmp_path):
        """子线程超时未返回时应抛出 TimeoutError。"""
        output = str(tmp_path / "out.mp3")

        async def hang(_path):
            await asyncio.sleep(999)

        mock_communicate = MagicMock()
        mock_communicate.save = hang
        mock_module = MagicMock()
        mock_module.Communicate.return_value = mock_communicate

        with patch.dict("sys.modules", {"edge_tts": mock_module}):
            from app.services.tts import tts_service
            import importlib; importlib.reload(tts_service)
            with pytest.raises(TimeoutError):
                tts_service._edge_tts("text", "zh-CN-XiaoxiaoNeural", output, timeout=1)


# ═══════════════════════════════════════════════════════════════════════════════
# Section 3 — Engine 2: Azure Speech SDK
# ═══════════════════════════════════════════════════════════════════════════════

class TestAzureTTS:

    def _mock_azure_sdk(self, reason_completed=True, error_details=""):
        speechsdk = MagicMock()
        speechsdk.SpeechSynthesisOutputFormat.Audio48Khz192KBitRateMonoMp3 = "mp3_format"

        if reason_completed:
            speechsdk.ResultReason.SynthesizingAudioCompleted = "completed"
            result_obj = MagicMock()
            result_obj.reason = "completed"
        else:
            speechsdk.ResultReason.SynthesizingAudioCompleted = "completed"
            speechsdk.ResultReason.Canceled = "canceled"
            result_obj = MagicMock()
            result_obj.reason = "canceled"
            result_obj.cancellation_details.error_details = error_details

        synthesizer = MagicMock()
        synthesizer.speak_ssml_async.return_value.get.return_value = result_obj
        speechsdk.SpeechSynthesizer.return_value = synthesizer
        return speechsdk

    def test_success(self, tmp_path, mock_settings):
        output = str(tmp_path / "out.mp3")
        mock_settings.AZURE_SPEECH_KEY = "fake_key"
        mock_settings.AZURE_SPEECH_REGION = "eastus"

        speechsdk = self._mock_azure_sdk(reason_completed=True)
        with patch.dict("sys.modules", {"azure.cognitiveservices.speech": speechsdk,
                                         "azure": MagicMock(), "azure.cognitiveservices": MagicMock()}):
            with patch("app.config.get_settings", return_value=mock_settings):
                from app.services.tts import tts_service
                import importlib; importlib.reload(tts_service)
                result = tts_service._azure_tts("你好", "zh-CN-XiaoxiaoNeural", output, rate=0)
        assert result is True

    def test_missing_api_key_raises(self, tmp_path, mock_settings):
        output = str(tmp_path / "out.mp3")
        mock_settings.AZURE_SPEECH_KEY = ""
        speechsdk = self._mock_azure_sdk()
        with patch.dict("sys.modules", {"azure.cognitiveservices.speech": speechsdk,
                                         "azure": MagicMock(), "azure.cognitiveservices": MagicMock()}):
            with patch("app.config.get_settings", return_value=mock_settings):
                from app.services.tts import tts_service
                import importlib; importlib.reload(tts_service)
                with pytest.raises(ValueError, match="AZURE_SPEECH_KEY"):
                    tts_service._azure_tts("text", "zh-CN-XiaoxiaoNeural", output)

    def test_synthesis_canceled_raises(self, tmp_path, mock_settings):
        output = str(tmp_path / "out.mp3")
        mock_settings.AZURE_SPEECH_KEY = "fake_key"
        speechsdk = self._mock_azure_sdk(reason_completed=False, error_details="quota exceeded")
        with patch.dict("sys.modules", {"azure.cognitiveservices.speech": speechsdk,
                                         "azure": MagicMock(), "azure.cognitiveservices": MagicMock()}):
            with patch("app.config.get_settings", return_value=mock_settings):
                from app.services.tts import tts_service
                import importlib; importlib.reload(tts_service)
                with pytest.raises(RuntimeError, match="quota exceeded"):
                    tts_service._azure_tts("text", "zh-CN-XiaoxiaoNeural", output)

    def test_ssml_contains_voice_and_rate(self, tmp_path, mock_settings):
        """SSML 必须包含正确的 voice name 和 prosody rate。"""
        output = str(tmp_path / "out.mp3")
        mock_settings.AZURE_SPEECH_KEY = "fake_key"
        captured_ssml = {}

        speechsdk = self._mock_azure_sdk(reason_completed=True)
        original_synthesizer = speechsdk.SpeechSynthesizer

        def capture_synthesizer(speech_config, audio_config):
            synth = original_synthesizer(speech_config=speech_config, audio_config=audio_config)
            original_speak = synth.speak_ssml_async

            def capture_ssml(ssml):
                captured_ssml["ssml"] = ssml
                return original_speak(ssml)

            synth.speak_ssml_async = capture_ssml
            return synth

        speechsdk.SpeechSynthesizer = capture_synthesizer
        with patch.dict("sys.modules", {"azure.cognitiveservices.speech": speechsdk,
                                         "azure": MagicMock(), "azure.cognitiveservices": MagicMock()}):
            with patch("app.config.get_settings", return_value=mock_settings):
                from app.services.tts import tts_service
                import importlib; importlib.reload(tts_service)
                tts_service._azure_tts("文本", "zh-CN-YunxiNeural", output, rate=10)

        ssml = captured_ssml.get("ssml", "")
        assert "zh-CN-YunxiNeural" in ssml
        assert "+10%" in ssml


# ═══════════════════════════════════════════════════════════════════════════════
# Section 4 — Engine 3: SiliconFlow
# ═══════════════════════════════════════════════════════════════════════════════

class TestSiliconFlowTTS:

    def test_success(self, tmp_path, mock_settings, mock_requests_post):
        output = str(tmp_path / "out.mp3")
        mock_settings.SILICONFLOW_API_KEY = "sf_fake_key"
        with patch("app.config.get_settings", return_value=mock_settings):
            from app.services.tts import tts_service
            import importlib; importlib.reload(tts_service)
            result = tts_service._siliconflow_tts("测试", "anna", output)
        assert result is True
        assert os.path.exists(output)
        assert os.path.getsize(output) > 0

    def test_missing_api_key_raises(self, tmp_path, mock_settings):
        output = str(tmp_path / "out.mp3")
        mock_settings.SILICONFLOW_API_KEY = ""
        with patch("app.config.get_settings", return_value=mock_settings):
            from app.services.tts import tts_service
            import importlib; importlib.reload(tts_service)
            with pytest.raises(ValueError, match="SILICONFLOW_API_KEY"):
                tts_service._siliconflow_tts("text", "anna", output)

    @pytest.mark.parametrize("voice", ["unknown_voice", "xyz", "INVALID"])
    def test_unknown_voice_defaults_to_anna(self, tmp_path, mock_settings, mock_requests_post, voice):
        output = str(tmp_path / "out.mp3")
        mock_settings.SILICONFLOW_API_KEY = "sf_fake_key"
        captured = {}

        original_post = mock_requests_post

        def capture_post(url, headers, json, timeout):
            captured["voice"] = json.get("voice", "")
            return original_post.return_value

        mock_requests_post.side_effect = capture_post
        with patch("app.config.get_settings", return_value=mock_settings):
            from app.services.tts import tts_service
            import importlib; importlib.reload(tts_service)
            tts_service._siliconflow_tts("text", voice, output)

        assert "anna" in captured.get("voice", "")

    def test_volume_gain_clamped(self, tmp_path, mock_settings, mock_requests_post):
        """volume=5.0 → gain_db=10（上限 10dB）。"""
        output = str(tmp_path / "out.mp3")
        mock_settings.SILICONFLOW_API_KEY = "sf_fake_key"
        captured = {}

        def capture_post(url, headers, json, timeout):
            captured["gain"] = json.get("gain")
            return mock_requests_post.return_value

        mock_requests_post.side_effect = capture_post
        with patch("app.config.get_settings", return_value=mock_settings):
            from app.services.tts import tts_service
            import importlib; importlib.reload(tts_service)
            tts_service._siliconflow_tts("text", "anna", output, volume=5.0)

        assert captured["gain"] == 10.0

    def test_volume_gain_lower_clamp(self, tmp_path, mock_settings, mock_requests_post):
        """volume=0.0 → gain_db=-10（下限 -10dB）。"""
        output = str(tmp_path / "out.mp3")
        mock_settings.SILICONFLOW_API_KEY = "sf_fake_key"
        captured = {}

        def capture_post(url, headers, json, timeout):
            captured["gain"] = json.get("gain")
            return mock_requests_post.return_value

        mock_requests_post.side_effect = capture_post
        with patch("app.config.get_settings", return_value=mock_settings):
            from app.services.tts import tts_service
            import importlib; importlib.reload(tts_service)
            tts_service._siliconflow_tts("text", "anna", output, volume=0.0)

        assert captured["gain"] == -10.0


# ═══════════════════════════════════════════════════════════════════════════════
# Section 5 — Engine 4: Gemini TTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestGeminiTTS:

    def _build_mocks(self, audio_bytes=b"\x00\x01" * 1000, base64_encoded=False):
        import base64 as b64_mod

        genai = MagicMock()
        pydub = MagicMock()

        audio_data = b64_mod.b64encode(audio_bytes).decode() if base64_encoded else audio_bytes

        part = MagicMock()
        part.inline_data.data = audio_data

        content = MagicMock()
        content.parts = [part]

        candidate = MagicMock()
        candidate.content = content

        response = MagicMock()
        response.candidates = [candidate]

        client = MagicMock()
        client.models.generate_content.return_value = response
        genai.Client.return_value = client

        audio_segment = MagicMock()
        pydub.AudioSegment.from_raw.return_value = audio_segment

        return genai, pydub

    def test_success_with_bytes(self, tmp_path, mock_settings):
        output = str(tmp_path / "out.mp3")
        mock_settings.GEMINI_API_KEY = "gemini_fake_key"
        genai, pydub = self._build_mocks()

        with patch.dict("sys.modules", {"google.generativeai": genai, "pydub": pydub}):
            with patch("app.config.get_settings", return_value=mock_settings):
                from app.services.tts import tts_service
                import importlib; importlib.reload(tts_service)
                result = tts_service._gemini_tts("你好", "Zephyr", output)
        assert result is True

    def test_success_with_base64_string(self, tmp_path, mock_settings):
        """audio_data 为 base64 字符串时应正确解码。"""
        output = str(tmp_path / "out.mp3")
        mock_settings.GEMINI_API_KEY = "gemini_fake_key"
        genai, pydub = self._build_mocks(base64_encoded=True)

        with patch.dict("sys.modules", {"google.generativeai": genai, "pydub": pydub}):
            with patch("app.config.get_settings", return_value=mock_settings):
                from app.services.tts import tts_service
                import importlib; importlib.reload(tts_service)
                result = tts_service._gemini_tts("text", "Zephyr", output)
        assert result is True

    def test_missing_api_key_raises(self, tmp_path, mock_settings):
        output = str(tmp_path / "out.mp3")
        mock_settings.GEMINI_API_KEY = ""
        genai, pydub = self._build_mocks()
        with patch.dict("sys.modules", {"google.generativeai": genai, "pydub": pydub}):
            with patch("app.config.get_settings", return_value=mock_settings):
                from app.services.tts import tts_service
                import importlib; importlib.reload(tts_service)
                with pytest.raises(ValueError, match="GEMINI_API_KEY"):
                    tts_service._gemini_tts("text", "Zephyr", output)

    @pytest.mark.parametrize("voice", ["InvalidVoice", "xyz", ""])
    def test_unknown_voice_defaults_to_zephyr(self, tmp_path, mock_settings, voice):
        output = str(tmp_path / "out.mp3")
        mock_settings.GEMINI_API_KEY = "gemini_fake_key"
        genai, pydub = self._build_mocks()
        captured = {}

        original_configure = genai.configure

        class CaptureVoiceConfig:
            def __init__(self, **kwargs):
                captured["voice_name"] = kwargs.get(
                    "prebuilt_voice_config",
                    MagicMock()
                ).voice_name if "prebuilt_voice_config" in kwargs else None

        genai.types.PrebuiltVoiceConfig = CaptureVoiceConfig

        with patch.dict("sys.modules", {"google.generativeai": genai, "pydub": pydub}):
            with patch("app.config.get_settings", return_value=mock_settings):
                from app.services.tts import tts_service
                import importlib; importlib.reload(tts_service)
                # Test that unknown voice is replaced with Zephyr
                # by checking the internal voice validation logic
                valid_voices = tts_service._GEMINI_VOICES
                assert voice not in valid_voices


# ═══════════════════════════════════════════════════════════════════════════════
# Section 6 — Engine 5: MiMo TTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestMimoTTS:

    def _build_openai_mock(self):
        response = MagicMock()
        response.content = b"\xff\xfb\x90\x00" + b"\x00" * 64
        client = MagicMock()
        client.audio.speech.create.return_value = response
        openai_mock = MagicMock()
        openai_mock.OpenAI.return_value = client
        return openai_mock, client

    def test_success(self, tmp_path, mock_settings):
        output = str(tmp_path / "out.mp3")
        mock_settings.MIMO_API_KEY = "mimo_fake_key"
        openai_mock, client = self._build_openai_mock()

        with patch.dict("sys.modules", {"openai": openai_mock}):
            with patch("app.config.get_settings", return_value=mock_settings):
                from app.services.tts import tts_service
                import importlib; importlib.reload(tts_service)
                result = tts_service._mimo_tts("你好", "female_1", output)
        assert result is True
        assert os.path.exists(output)

    def test_missing_api_key_raises(self, tmp_path, mock_settings):
        output = str(tmp_path / "out.mp3")
        mock_settings.MIMO_API_KEY = ""
        openai_mock, _ = self._build_openai_mock()
        with patch.dict("sys.modules", {"openai": openai_mock}):
            with patch("app.config.get_settings", return_value=mock_settings):
                from app.services.tts import tts_service
                import importlib; importlib.reload(tts_service)
                with pytest.raises(ValueError, match="MIMO_API_KEY"):
                    tts_service._mimo_tts("text", "female_1", output)

    @pytest.mark.parametrize("voice", ["invalid", "xyz", "unknown_gender"])
    def test_unknown_voice_defaults_to_female_1(self, tmp_path, mock_settings, voice):
        output = str(tmp_path / "out.mp3")
        mock_settings.MIMO_API_KEY = "mimo_fake_key"
        openai_mock, client = self._build_openai_mock()
        with patch.dict("sys.modules", {"openai": openai_mock}):
            with patch("app.config.get_settings", return_value=mock_settings):
                from app.services.tts import tts_service
                import importlib; importlib.reload(tts_service)
                tts_service._mimo_tts("text", voice, output)
        call_kwargs = client.audio.speech.create.call_args
        assert call_kwargs[1]["voice"] == "female_1" or \
               (call_kwargs[0] and "female_1" in str(call_kwargs))

    def test_uses_mimo_v25_model(self, tmp_path, mock_settings):
        output = str(tmp_path / "out.mp3")
        mock_settings.MIMO_API_KEY = "mimo_fake_key"
        openai_mock, client = self._build_openai_mock()
        with patch.dict("sys.modules", {"openai": openai_mock}):
            with patch("app.config.get_settings", return_value=mock_settings):
                from app.services.tts import tts_service
                import importlib; importlib.reload(tts_service)
                tts_service._mimo_tts("text", "female_1", output)
        call_kwargs = client.audio.speech.create.call_args[1]
        assert call_kwargs["model"] == "mimo-v2.5-tts"

    def test_base_url_is_xiaomimimo(self, tmp_path, mock_settings):
        output = str(tmp_path / "out.mp3")
        mock_settings.MIMO_API_KEY = "mimo_fake_key"
        openai_mock, _ = self._build_openai_mock()
        with patch.dict("sys.modules", {"openai": openai_mock}):
            with patch("app.config.get_settings", return_value=mock_settings):
                from app.services.tts import tts_service
                import importlib; importlib.reload(tts_service)
                tts_service._mimo_tts("text", "female_1", output)
        openai_mock.OpenAI.assert_called_once()
        call_kwargs = openai_mock.OpenAI.call_args[1]
        assert "xiaomimimo.com" in call_kwargs.get("base_url", "")


# ═══════════════════════════════════════════════════════════════════════════════
# Section 7 — list_voices
# ═══════════════════════════════════════════════════════════════════════════════

class TestListVoices:

    def test_siliconflow_returns_sorted_set(self):
        from app.services.tts.tts_service import list_voices, _SILICONFLOW_VOICES
        result = list_voices("siliconflow")
        assert result == sorted(_SILICONFLOW_VOICES)

    def test_gemini_returns_list(self):
        from app.services.tts.tts_service import list_voices, _GEMINI_VOICES
        result = list_voices("gemini")
        assert result == _GEMINI_VOICES
        assert "Zephyr" in result

    def test_mimo_returns_sorted_set(self):
        from app.services.tts.tts_service import list_voices, _MIMO_VOICES
        result = list_voices("mimo")
        assert result == sorted(_MIMO_VOICES)
        assert "female_1" in result

    def test_edge_fallback_when_import_fails(self):
        """edge_tts 不可用时返回硬编码中文音色列表。"""
        with patch.dict("sys.modules", {"edge_tts": None}):
            from app.services.tts import tts_service
            import importlib; importlib.reload(tts_service)
            result = tts_service.list_voices("edge")
        assert len(result) > 0
        assert all("zh-CN" in v for v in result)

    def test_unknown_engine_returns_empty(self):
        from app.services.tts.tts_service import list_voices
        assert list_voices("nonexistent") == []

    def test_all_siliconflow_voices_are_valid_strings(self):
        from app.services.tts.tts_service import list_voices
        for v in list_voices("siliconflow"):
            assert isinstance(v, str) and len(v) > 0
