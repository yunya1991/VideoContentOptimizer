"""
TTS 服务模块 — 6 种引擎统一接口
移植自 MoneyPrinterTurbo/app/services/tts/voice.py
"""
import asyncio
import os
import queue
import threading
from typing import Optional
from app.utils.logger import logger


def tts(
    text: str,
    voice_name: str,
    output_file: str,
    voice_rate: int = 0,
    voice_volume: float = 1.0,
) -> bool:
    """
    统一 TTS 入口，按 voice_name 前缀路由到对应引擎。

    voice_name 约定：
      edge:zh-CN-XiaoxiaoNeural      免费，默认
      azure:zh-CN-XiaoxiaoNeural     Azure Speech SDK（付费高质量）
      siliconflow:anna               CosyVoice2（国内免费额度）
      gemini:Zephyr                  Gemini TTS
      mimo:female_1                  小米 MiMo TTS
      直接传声音名                    默认走 edge_tts
    """
    engine, _, name = voice_name.partition(":")
    name = name or voice_name

    try:
        if engine == "azure":
            return _azure_tts(text, name, output_file, voice_rate)
        elif engine == "siliconflow":
            return _siliconflow_tts(text, name, output_file, voice_volume)
        elif engine == "gemini":
            return _gemini_tts(text, name, output_file)
        elif engine == "mimo":
            return _mimo_tts(text, name, output_file)
        else:
            return _edge_tts(text, name or "zh-CN-XiaoxiaoNeural", output_file, voice_rate)
    except Exception as e:
        logger.error(f"TTS 失败 [{engine}]: {e}")
        return False


# ─── Engine 1: edge_tts（免费，默认）────────────────────────────────────────

def _edge_tts(text: str, voice: str, output_file: str, rate: int = 0, timeout: int = 60) -> bool:
    try:
        import edge_tts
    except ImportError:
        raise ImportError("请安装: pip install edge-tts")

    rate_str = f"+{rate}%" if rate >= 0 else f"{rate}%"
    result_queue: queue.Queue = queue.Queue()

    def _run():
        async def _inner():
            communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate_str)
            await communicate.save(output_file)
        try:
            asyncio.run(_inner())
            result_queue.put(True)
        except Exception as e:
            result_queue.put(e)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    try:
        result = result_queue.get(timeout=timeout)
    except queue.Empty:
        raise TimeoutError(f"edge_tts 超时 ({timeout}s)")

    if isinstance(result, Exception):
        raise result
    if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
        raise RuntimeError("edge_tts 生成空文件")
    return True


# ─── Engine 2: Azure Speech SDK（高质量，付费）──────────────────────────────

def _azure_tts(text: str, voice: str, output_file: str, rate: int = 0) -> bool:
    try:
        import azure.cognitiveservices.speech as speechsdk
    except ImportError:
        raise ImportError("请安装: pip install azure-cognitiveservices-speech")

    from app.config import get_settings
    s = get_settings()
    speech_key = getattr(s, "AZURE_SPEECH_KEY", "") or os.environ.get("AZURE_SPEECH_KEY", "")
    speech_region = getattr(s, "AZURE_SPEECH_REGION", "eastus") or os.environ.get("AZURE_SPEECH_REGION", "eastus")

    if not speech_key:
        raise ValueError("AZURE_SPEECH_KEY 未配置")

    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio48Khz192KBitRateMonoMp3
    )

    rate_str = f"+{rate}%" if rate >= 0 else f"{rate}%"
    ssml = (
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN">'
        f'<voice name="{voice}"><prosody rate="{rate_str}">{text}</prosody></voice></speak>'
    )

    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_file)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    result = synthesizer.speak_ssml_async(ssml).get()

    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        details = ""
        if result.reason == speechsdk.ResultReason.Canceled:
            details = result.cancellation_details.error_details
        raise RuntimeError(f"Azure TTS 失败: {details or result.reason}")
    return True


# ─── Engine 3: SiliconFlow CosyVoice2（国内免费额度）────────────────────────

_SILICONFLOW_VOICES = {"alex", "anna", "bella", "benjamin", "charles", "claire", "david", "diana"}


def _siliconflow_tts(text: str, voice: str, output_file: str, volume: float = 1.0) -> bool:
    import requests
    from app.config import get_settings

    s = get_settings()
    api_key = getattr(s, "SILICONFLOW_API_KEY", "") or os.environ.get("SILICONFLOW_API_KEY", "")
    if not api_key:
        raise ValueError("SILICONFLOW_API_KEY 未配置")

    if voice not in _SILICONFLOW_VOICES:
        voice = "anna"

    gain_db = round((volume - 1.0) * 10, 1)
    gain_db = max(-10.0, min(10.0, gain_db))

    resp = requests.post(
        "https://api.siliconflow.cn/v1/audio/speech",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": "FunAudioLLM/CosyVoice2-0.5B",
            "input": text,
            "voice": f"FunAudioLLM/CosyVoice2-0.5B:{voice}",
            "gain": gain_db,
        },
        timeout=60,
    )
    resp.raise_for_status()

    with open(output_file, "wb") as f:
        f.write(resp.content)
    return True


# ─── Engine 4: Gemini TTS ────────────────────────────────────────────────────

_GEMINI_VOICES = [
    "Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Aoede",
    "Callirrhoe", "Autonoe", "Enceladus", "Iapetus", "Umbriel", "Algieba",
    "Despina", "Erinome", "Algenib", "Rasalgethi", "Laomedeia", "Achernar",
]


def _gemini_tts(text: str, voice: str, output_file: str) -> bool:
    try:
        import google.generativeai as genai
        from pydub import AudioSegment
        import io
    except ImportError:
        raise ImportError("请安装: pip install google-generativeai pydub")

    from app.config import get_settings
    s = get_settings()
    api_key = getattr(s, "GEMINI_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 未配置")

    if voice not in _GEMINI_VOICES:
        voice = "Zephyr"

    genai.configure(api_key=api_key)
    client = genai.Client()
    response = client.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
        contents=text,
        config=genai.types.GenerateContentConfig(
            speech_config=genai.types.SpeechConfig(
                voice_config=genai.types.VoiceConfig(
                    prebuilt_voice_config=genai.types.PrebuiltVoiceConfig(voice_name=voice)
                )
            )
        ),
    )

    audio_data = response.candidates[0].content.parts[0].inline_data.data
    if isinstance(audio_data, str):
        import base64
        audio_data = base64.b64decode(audio_data)

    audio = AudioSegment.from_raw(io.BytesIO(audio_data), sample_width=2, frame_rate=24000, channels=1)
    audio.export(output_file, format="mp3")
    return True


# ─── Engine 5: MiMo TTS（小米）──────────────────────────────────────────────

_MIMO_VOICES = {"male_1", "male_2", "male_3", "female_1", "female_2", "female_3", "child_1", "narrator_1", "anchor_1"}


def _mimo_tts(text: str, voice: str, output_file: str, style_prompt: str = "") -> bool:
    from openai import OpenAI
    from app.config import get_settings

    s = get_settings()
    api_key = getattr(s, "MIMO_API_KEY", "") or os.environ.get("MIMO_API_KEY", "")
    if not api_key:
        raise ValueError("MIMO_API_KEY 未配置")

    if voice not in _MIMO_VOICES:
        voice = "female_1"

    client = OpenAI(api_key=api_key, base_url="https://api.xiaomimimo.com/v1")
    extra = {"style_prompt": style_prompt} if style_prompt else {}
    response = client.audio.speech.create(model="mimo-v2.5-tts", voice=voice, input=text, extra_body=extra)

    with open(output_file, "wb") as f:
        f.write(response.content)
    return True


# ─── 工具：列出各引擎可用声音 ────────────────────────────────────────────────

def list_voices(engine: str = "edge") -> list:
    if engine == "siliconflow":
        return sorted(_SILICONFLOW_VOICES)
    if engine == "gemini":
        return _GEMINI_VOICES
    if engine == "mimo":
        return sorted(_MIMO_VOICES)
    if engine == "edge":
        try:
            import edge_tts
            voices = asyncio.run(edge_tts.list_voices())
            return [v["ShortName"] for v in voices if "zh-CN" in v["ShortName"]]
        except Exception:
            return ["zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural", "zh-CN-YunjianNeural"]
    return []
