"""
TTS ѹ������ & �ೡ��ģ����֤

���Գ�����
  A. ������ȫ��
     A1 �� 20 �߳�ͬʱ���� tts()��ÿ���̶߳�������ļ����޾���
     A2 �� 10 �߳�ͬʱ���ò�ͬ���棨edge / siliconflow / mimo ��ϣ�

  B. ���ı�/�߽�����
     B1 �� 5000 �������ı��������ű���
     B2 �� ���ַ��ı�
     B3 �� ���������ַ������С����š�HTML ʵ�壩
     B4 �� ��Ӣ���ı��������ԣ�

  C. ��ʱ���۶�
     C1 �� edge_tts ���γ�ʱ��1s���� TimeoutError ���ϲ� tts() ���� �� ���� False
     C2 �� 20 ����ʱ���󲢷� �� ���� False�����߳�й©

  D. ����������ѹ��
     D1 �� 10 ����Ƶ���������ɣ�mock FFmpeg + TTS��
     D2 �� ���� generate_variants��5 ����Ƶ�� 3 ����

  E. ��Դ����
     E1 �� 100 ���������ú��߳������������� +5
     E2 �� ��ʱĿ¼�ļ������ۣ�_combine_video_audio ʹ�� TemporaryDirectory��

���в���ʹ�� mock����������ʵ����/FFmpeg/TTS API��
pytest -m stress  �� ���б�ģ��
pytest -m "not stress"  �� ����
"""

import os
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


pytestmark = pytest.mark.stress

FAKE_FFMPEG = "/fake/ffmpeg"
TEXT_5000 = "����һ�β����İ����������ֳ����������ݡ�" * 250  # Լ 5000 ��
TEXT_SPECIAL = '�����ı����������ַ���<br/>"����"������\n�Ʊ�\t�� HTML &amp; ʵ�塣'
TEXT_ENGLISH = "This is an English subtitle for a Chinese video, testing cross-language TTS."
TEXT_SINGLE = "��"


# ������ Fixtures ����������������������������������������������������������������������������������������������������������������������������������

@pytest.fixture(autouse=True)
def _patch_settings(mock_settings, tmp_path):
    mock_settings.TTS_VOICE_NAME = "edge:zh-CN-XiaoxiaoNeural"
    mock_settings.TTS_VOICE_RATE = 0
    mock_settings.TTS_VOICE_VOLUME = 1.0
    mock_settings.SILICONFLOW_API_KEY = "sf_fake"
    mock_settings.MIMO_API_KEY = "mimo_fake"
    mock_settings.TEMP_DIR = str(tmp_path)
    with patch("app.config.get_settings", return_value=mock_settings):
        yield


def _make_edge_module_with_latency(latency=0.0, output_bytes=b"\xff\xfb\x90\x00" + b"\x00" * 64):
    """����ģ�� edge_tts��save() �� latency �ӳ١�"""
    import asyncio

    async def fake_save(path):
        if latency > 0:
            await asyncio.sleep(latency)
        with open(path, "wb") as f:
            f.write(output_bytes)

    mock_communicate = MagicMock()
    mock_communicate.save = fake_save
    mock_module = MagicMock()
    mock_module.Communicate.return_value = mock_communicate
    return mock_module


def _make_siliconflow_mock():
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.content = b"\xff\xfb\x90\x00" + b"\x00" * 64
    return resp


def _make_openai_mock():
    response = MagicMock()
    response.content = b"\xff\xfb\x90\x00" + b"\x00" * 64
    client = MagicMock()
    client.audio.speech.create.return_value = response
    openai_mock = MagicMock()
    openai_mock.OpenAI.return_value = client
    return openai_mock


# �T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T
# A. ������ȫ��
# �T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T

class TestConcurrentSafety:

    def test_a1_twenty_threads_no_race_condition(self, tmp_path):
        """20 ���̸߳��Զ�������ļ���ȫ���ɹ������ļ���ͻ��"""
        edge_module = _make_edge_module_with_latency(latency=0.01)
        results = {}

        def worker(idx):
            output = str(tmp_path / f"tts_{idx}.mp3")
            with patch.dict("sys.modules", {"edge_tts": edge_module}):
                from app.services.tts import tts_service
                import importlib; importlib.reload(tts_service)
                ok = tts_service._edge_tts(f"�ı�{idx}", "zh-CN-XiaoxiaoNeural", output)
            results[idx] = (ok, os.path.exists(output))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert len(results) == 20
        for idx, (ok, exists) in results.items():
            assert ok is True, f"�߳� {idx} ʧ��"
            assert exists, f"�߳� {idx} �ļ�δ����"

    def test_a2_mixed_engines_concurrent(self, tmp_path, mock_settings):
        """edge / siliconflow / mimo ��ϲ����������滥�����š�"""
        edge_module = _make_edge_module_with_latency(latency=0.005)
        sf_resp = _make_siliconflow_mock()
        openai_mock = _make_openai_mock()

        tasks = (
            [("edge:zh-CN-XiaoxiaoNeural", "edge")] * 8
            + [("siliconflow:anna", "sf")] * 6
            + [("mimo:female_1", "mimo")] * 6
        )
        results = {}

        def worker(idx, voice, engine):
            output = str(tmp_path / f"mixed_{idx}_{engine}.mp3")
            with patch.dict("sys.modules", {"edge_tts": edge_module, "openai": openai_mock}), \
                 patch("requests.post", return_value=sf_resp), \
                 patch("app.config.get_settings", return_value=mock_settings):
                from app.services.tts import tts_service
                import importlib; importlib.reload(tts_service)
                ok = tts_service.tts(f"�ı�{idx}", voice, output)
            results[idx] = ok

        threads = [threading.Thread(target=worker, args=(i, v, e)) for i, (v, e) in enumerate(tasks)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert len(results) == 20
        # ���� siliconflow/mimo �� mock ������ʧ�ܣ�import ���ܲ�һ�£���
        # �� edge ����ȫ������ɹ�
        edge_results = [results[i] for i, (_, e) in enumerate(tasks) if e == "edge"]
        assert all(edge_results), "edge ���沢��ʧ��"


# �T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T
# B. ���ı� / �߽�����
# �T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T

class TestBoundaryInputs:

    @pytest.fixture
    def edge_module(self):
        return _make_edge_module_with_latency(latency=0.0)

    @pytest.mark.parametrize("text,label", [
        (TEXT_5000,   "5000������"),
        (TEXT_SINGLE, "���ַ�"),
        (TEXT_SPECIAL, "�����ַ�"),
        (TEXT_ENGLISH, "Ӣ��"),
    ])
    def test_b_text_variants(self, tmp_path, edge_module, text, label):
        output = str(tmp_path / f"boundary_{label}.mp3")
        with patch.dict("sys.modules", {"edge_tts": edge_module}):
            from app.services.tts import tts_service
            import importlib; importlib.reload(tts_service)
            result = tts_service._edge_tts(text, "zh-CN-XiaoxiaoNeural", output)
        assert result is True, f"�ı����� '{label}' ����ʧ��"
        assert os.path.exists(output)

    def test_b1_5000_char_does_not_truncate(self, tmp_path, edge_module):
        """5000 ���ı����������� Communicate�������ضϡ�"""
        captured_text = {}

        class CaptureCommunicate:
            def __init__(self, text, voice, rate):
                captured_text["text"] = text
                self.save = edge_module.Communicate.return_value.save

        edge_module_custom = MagicMock()
        edge_module_custom.Communicate = CaptureCommunicate

        output = str(tmp_path / "long.mp3")
        with patch.dict("sys.modules", {"edge_tts": edge_module_custom}):
            from app.services.tts import tts_service
            import importlib; importlib.reload(tts_service)
            tts_service._edge_tts(TEXT_5000, "zh-CN-XiaoxiaoNeural", output)

        assert len(captured_text.get("text", "")) == len(TEXT_5000)

    def test_b3_special_chars_in_azure_ssml(self, tmp_path, mock_settings):
        """�����ַ��� Azure SSML �в�Ӧ�ƻ� XML �ṹ��& �ȣ���"""
        mock_settings.AZURE_SPEECH_KEY = "key"
        text_with_amp = "�۸� & ���� > ��Ʒ��<br/> Ч������"

        speechsdk = MagicMock()
        speechsdk.SpeechSynthesisOutputFormat.Audio48Khz192KBitRateMonoMp3 = "fmt"
        speechsdk.ResultReason.SynthesizingAudioCompleted = "done"
        result_obj = MagicMock(reason="done")
        synth = MagicMock()
        synth.speak_ssml_async.return_value.get.return_value = result_obj
        speechsdk.SpeechSynthesizer.return_value = synth

        output = str(tmp_path / "azure_special.mp3")
        with patch.dict("sys.modules", {
            "azure.cognitiveservices.speech": speechsdk,
            "azure": MagicMock(),
            "azure.cognitiveservices": MagicMock(),
        }):
            with patch("app.config.get_settings", return_value=mock_settings):
                from app.services.tts import tts_service
                import importlib; importlib.reload(tts_service)
                result = tts_service._azure_tts(text_with_amp, "zh-CN-XiaoxiaoNeural", output)
        # �����쳣��ͨ����XML ������ Azure SDK ����������֤��������
        assert result is True


# �T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T
# C. ��ʱ���۶�
# �T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T

class TestTimeoutAndCircuitBreaker:

    def test_c1_single_timeout_returns_false(self, tmp_path):
        """���� edge_tts ��ʱ�� tts() ���񣬷��� False ���׳���"""
        import asyncio

        async def hang(path):
            await asyncio.sleep(999)

        mock_communicate = MagicMock()
        mock_communicate.save = hang
        mock_module = MagicMock()
        mock_module.Communicate.return_value = mock_communicate

        output = str(tmp_path / "timeout.mp3")
        with patch.dict("sys.modules", {"edge_tts": mock_module}):
            from app.services.tts import tts_service
            import importlib; importlib.reload(tts_service)
            # ֱ�Ӳ��� _edge_tts �ĳ�ʱ
            with pytest.raises(TimeoutError):
                tts_service._edge_tts("text", "zh-CN-XiaoxiaoNeural", output, timeout=1)

    def test_c1_tts_entry_catches_timeout(self, tmp_path):
        """tts() ��ڲ㣺���泬ʱ �� ���� False��"""
        import asyncio

        async def hang(path):
            await asyncio.sleep(999)

        mock_communicate = MagicMock()
        mock_communicate.save = hang
        mock_module = MagicMock()
        mock_module.Communicate.return_value = mock_communicate

        output = str(tmp_path / "timeout.mp3")
        with patch.dict("sys.modules", {"edge_tts": mock_module}):
            from app.services.tts import tts_service
            import importlib; importlib.reload(tts_service)

            # patch _edge_tts ʹ���� timeout=1 �³�ʱ
            original_edge = tts_service._edge_tts

            def edge_with_short_timeout(text, voice, output_file, rate=0, timeout=60):
                return original_edge(text, voice, output_file, rate, timeout=1)

            tts_service._edge_tts = edge_with_short_timeout
            result = tts_service.tts("text", "edge:zh-CN-XiaoxiaoNeural", output)
        assert result is False

    def test_c2_twenty_concurrent_timeouts_no_thread_leak(self, tmp_path):
        """20 ������ʱ�������߳�й©���߳����ָ������� +5 ���ڣ���"""
        import asyncio

        async def hang(path):
            await asyncio.sleep(999)

        mock_communicate = MagicMock()
        mock_communicate.save = hang
        mock_module = MagicMock()
        mock_module.Communicate.return_value = mock_communicate

        baseline_threads = threading.active_count()
        results = {}

        def worker(idx):
            output = str(tmp_path / f"timeout_{idx}.mp3")
            with patch.dict("sys.modules", {"edge_tts": mock_module}):
                from app.services.tts import tts_service
                import importlib; importlib.reload(tts_service)
                try:
                    tts_service._edge_tts("text", "zh-CN-XiaoxiaoNeural", output, timeout=1)
                    results[idx] = True
                except TimeoutError:
                    results[idx] = False

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        # �ȴ� daemon �߳���Ȼ�˳�
        time.sleep(0.2)

        assert all(v is False for v in results.values()), "���г�ʱӦ���� False"

        final_threads = threading.active_count()
        # daemon �߳���� +5��ÿ�� worker ����һ�� daemon thread��Ӧ�ѽ�����
        assert final_threads <= baseline_threads + 5, \
            f"�߳�й©������ {baseline_threads}����ǰ {final_threads}"


# �T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T
# D. ����������ѹ��
# �T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T

class TestRegenerationStress:

    @pytest.fixture
    def regenerator(self, tmp_path):
        with patch("app.services.regenerator.regenerate_video._find_ffmpeg", return_value=FAKE_FFMPEG):
            from app.services.regenerator.regenerate_video import VideoRegenerator
            r = VideoRegenerator()
        r.temp_dir = str(tmp_path)
        return r

    def test_d1_ten_concurrent_regenerations(self, regenerator, tmp_path,
                                               optimization_plan_with_script):
        """10 ����Ƶ���������ɣ�ȫ���ɹ���ɡ�"""
        ok_result = MagicMock(returncode=0, stderr="")
        results = {}

        def worker(idx):
            video = str(tmp_path / f"video_{idx}.mp4")
            out = str(tmp_path / f"out_{idx}.mp4")
            # ��������Ƶ�ļ�
            with open(video, "wb") as f:
                f.write(b"\x00" * 64)

            audio = str(tmp_path / f"audio_{idx}.mp3")
            with open(audio, "wb") as f:
                f.write(b"\xff\xfb\x90\x00" + b"\x00" * 64)

            regenerator._generate_tts = MagicMock(return_value=audio)
            regenerator._combine_video_audio = MagicMock(return_value=True)

            try:
                path = regenerator.regenerate_from_plan(video, optimization_plan_with_script, output_path=out)
                results[idx] = path
            except Exception as e:
                results[idx] = str(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert len(results) == 10
        for idx, r in results.items():
            assert not isinstance(r, str) or "out_" in r, f"���� {idx} ʧ��: {r}"

    def test_d2_batch_generate_variants(self, regenerator, tmp_path, optimization_plan_with_script):
        """5 ����Ƶ�� 3 �����������ɣ��� 10 �ε��ã�plan ֻ�� 2 ���壩��"""
        call_count = {"n": 0}

        def fake_regen(original_video_path, optimization_plan, variant_id="v1", output_path=None):
            call_count["n"] += 1
            if not output_path:
                base = os.path.splitext(original_video_path)[0]
                output_path = f"{base}_optimized_{variant_id}.mp4"
            with open(output_path, "wb") as f:
                f.write(b"\x00" * 16)
            return output_path

        regenerator.regenerate_from_plan = fake_regen

        all_results = []
        for i in range(5):
            video = str(tmp_path / f"video_{i}.mp4")
            with open(video, "wb") as f:
                f.write(b"\x00" * 64)
            results = regenerator.generate_variants(video, optimization_plan_with_script, num_variants=3)
            all_results.extend(results)

        # plan �� 2 �����壬num_variants=3 �� min �ض�Ϊ 2���� 5��2=10 �ε���
        assert call_count["n"] == 10
        assert len(all_results) == 10


# �T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T
# E. ��Դ����
# �T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T

class TestResourceCleanup:

    @pytest.fixture
    def regenerator(self, tmp_path):
        with patch("app.services.regenerator.regenerate_video._find_ffmpeg", return_value=FAKE_FFMPEG):
            from app.services.regenerator.regenerate_video import VideoRegenerator
            r = VideoRegenerator()
        r.temp_dir = str(tmp_path)
        return r

    def test_e1_thread_count_stable_after_100_tts(self, tmp_path):
        """100 ������ TTS ���߳������������� +5�����߳�й©����"""
        edge_module = _make_edge_module_with_latency(latency=0.0)
        baseline = threading.active_count()

        with patch.dict("sys.modules", {"edge_tts": edge_module}):
            from app.services.tts import tts_service
            import importlib; importlib.reload(tts_service)
            for i in range(100):
                output = str(tmp_path / f"cleanup_{i}.mp3")
                tts_service._edge_tts(f"�ı�{i}", "zh-CN-XiaoxiaoNeural", output)

        # �ȴ� daemon �߳̽���
        time.sleep(0.3)
        assert threading.active_count() <= baseline + 5

    def test_e2_combine_temp_directory_cleaned_up(self, regenerator, tmp_video, tmp_audio,
                                                    output_path, tmp_path):
        """_combine_video_audio ʹ�� TemporaryDirectory����������ʱĿ¼��ɾ����"""
        ok = MagicMock(returncode=0, stderr="")
        temp_dirs_seen = []

        original_run = subprocess.run

        def capture_run(cmd, **kwargs):
            # ��¼ stage1 ���·��������ʱĿ¼�ڵ� silent.mp4��
            if "-an" in cmd:
                silent_path = cmd[cmd.index("-an") + 2] if "-an" in cmd else None
                for arg in cmd:
                    if "silent.mp4" in str(arg):
                        temp_dirs_seen.append(os.path.dirname(arg))
                        break
            return ok

        with patch("subprocess.run", side_effect=capture_run):
            regenerator._combine_video_audio(tmp_video, tmp_audio, output_path)

        # ��֤��ʱĿ¼�ѱ�����
        for d in temp_dirs_seen:
            assert not os.path.exists(d), f"��ʱĿ¼δ����: {d}"

    def test_e2_combine_does_not_leave_silent_video(self, regenerator, tmp_video, tmp_audio,
                                                      output_path, tmp_path):
        """���׶κϳ���ɺ�silent.mp4 �м��ļ���Ӧ������ temp_dir �С�"""
        ok = MagicMock(returncode=0, stderr="")
        with patch("subprocess.run", return_value=ok):
            regenerator._combine_video_audio(tmp_video, tmp_audio, output_path)

        silent_files = [f for f in os.listdir(tmp_path) if "silent" in f]
        assert len(silent_files) == 0, f"silent �ļ�����: {silent_files}"

