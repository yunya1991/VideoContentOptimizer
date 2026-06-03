"""
视频重生成模块 — P0 修复版
修复内容：
  1. _generate_tts: 接入 6 种 TTS 引擎（edge_tts 为默认免费方案）
  2. _combine_video_audio: 移植 MoneyPrinterTurbo 两阶段 FFmpeg 合成
  3. _find_ffmpeg: 跨平台 FFmpeg 路径查找（env → PATH → imageio_ffmpeg）
"""

import json
import os
import shutil
import subprocess
import tempfile
from typing import List, Optional

from app.config import get_settings
from app.models.schema import VideoAnalysisResult, OptimizationPlan
from app.services.tts.tts_service import tts as run_tts
from app.utils.logger import logger

settings = get_settings()


def _find_ffmpeg() -> str:
    """
    跨平台 FFmpeg 路径查找（三级优先级）：
      1. 环境变量 IMAGEIO_FFMPEG_EXE / FFMPEG_PATH
      2. 系统 PATH（shutil.which）
      3. imageio_ffmpeg 打包版本
    """
    # 1. 环境变量
    for env_var in ("IMAGEIO_FFMPEG_EXE", "FFMPEG_PATH"):
        path = os.environ.get(env_var, "")
        if path and os.path.isfile(path):
            return path

    # 2. config 中配置的路径（非默认值时优先）
    configured = getattr(settings, "FFMPEG_PATH", "")
    if configured and configured != "/usr/bin/ffmpeg" and os.path.isfile(configured):
        return configured

    # 3. 系统 PATH
    found = shutil.which("ffmpeg")
    if found:
        return found

    # 4. imageio_ffmpeg 打包版本（pip install imageio-ffmpeg）
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass

    raise RuntimeError(
        "找不到 FFmpeg。请安装 FFmpeg 并确保其在 PATH 中，"
        "或设置环境变量 FFMPEG_PATH，或运行: pip install imageio-ffmpeg"
    )


class VideoRegenerator:
    """根据优化方案重新生成视频"""

    def __init__(self):
        self.ffmpeg_path = _find_ffmpeg()
        self.temp_dir = settings.TEMP_DIR
        os.makedirs(self.temp_dir, exist_ok=True)
        logger.info(f"VideoRegenerator 初始化，FFmpeg: {self.ffmpeg_path}")

    # ─── 公开接口 ──────────────────────────────────────────────────────────

    def regenerate_from_plan(
        self,
        original_video_path: str,
        optimization_plan: OptimizationPlan,
        variant_id: str = "v1",
        output_path: Optional[str] = None,
    ) -> str:
        if not output_path:
            base_name = os.path.splitext(original_video_path)[0]
            output_path = f"{base_name}_optimized_{variant_id}.mp4"

        try:
            new_audio_path = None
            srt_path = None
            if optimization_plan.script_optimization:
                new_script = optimization_plan.script_optimization.optimized_script
                new_audio_path, srt_path = self._generate_tts_and_srt(new_script)

            if new_audio_path:
                self._combine_video_audio(original_video_path, new_audio_path, output_path)
            else:
                shutil.copy2(original_video_path, output_path)

            if srt_path and os.path.exists(srt_path):
                subtitled_path = output_path.replace(".mp4", "_sub.mp4")
                if self._burn_subtitles(output_path, srt_path, subtitled_path):
                    shutil.move(subtitled_path, output_path)

            return output_path

        except Exception as e:
            raise RuntimeError(f"视频重生成失败: {str(e)}")

    def generate_variants(
        self,
        original_video_path: str,
        plan: OptimizationPlan,
        num_variants: int = 3,
    ) -> List[str]:
        results = []
        for i in range(min(num_variants, len(plan.creative_variants))):
            variant = plan.creative_variants[i]
            output_path = self.regenerate_from_plan(
                original_video_path=original_video_path,
                optimization_plan=plan,
                variant_id=variant.variant_id,
            )
            results.append(output_path)
        return results

    def apply_platform_template(
        self,
        video_path: str,
        platform: str,
        output_path: Optional[str] = None,
    ) -> str:
        if not output_path:
            base_name = os.path.splitext(video_path)[0]
            output_path = f"{base_name}_{platform}.mp4"

        template_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "resource", "templates", f"{platform}_template.json",
        )

        if not os.path.exists(template_path):
            shutil.copy2(video_path, output_path)
            return output_path

        try:
            with open(template_path, "r", encoding="utf-8") as f:
                template = json.load(f)

            target_resolution = template.get("optimal_specs", {}).get("resolution", "1920x1080")
            width, height = map(int, target_resolution.split("x"))

            cmd = [
                self.ffmpeg_path, "-i", video_path,
                "-vf", f"scale={width}:{height}",
                "-c:a", "copy", output_path, "-y",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg 失败: {result.stderr}")
            return output_path

        except Exception as e:
            logger.warning(f"应用平台模板失败: {e}")
            shutil.copy2(video_path, output_path)
            return output_path

    # ─── 私有方法 ──────────────────────────────────────────────────────────

    def _generate_tts_and_srt(self, text: str) -> tuple:
        """
        生成 TTS 音频并（可选）创建对应 SRT 字幕文件。

        返回: (audio_path_or_None, srt_path_or_None)
        字幕仅在 settings.SUBTITLE_ENABLED=True 且音频生成成功时生成。
        """
        audio_path = self._generate_tts(text)

        subtitle_enabled = getattr(settings, "SUBTITLE_ENABLED", False)
        if not audio_path or not subtitle_enabled:
            return audio_path, None

        try:
            duration = self._get_audio_duration_seconds(audio_path)
            from app.services.subtitle.sub_maker import SubMaker
            maker = SubMaker.from_timed_text(text, duration)
            srt_path = audio_path.replace(".mp3", ".srt")
            maker.save_srt(srt_path)
            logger.info(f"字幕文件生成: {srt_path}, {len(maker.cues)} 条")
            return audio_path, srt_path
        except Exception as e:
            logger.warning(f"字幕生成失败（非致命）: {e}")
            return audio_path, None

    def _get_audio_duration_seconds(self, audio_path: str) -> float:
        """
        获取音频时长（秒）。
        优先使用 ffprobe，失败则按中文平均语速估算（约 4.5 字/秒）。
        """
        try:
            ffprobe = self.ffmpeg_path.replace("ffmpeg", "ffprobe")
            if not os.path.isfile(ffprobe):
                ffprobe = shutil.which("ffprobe") or ""
            if ffprobe:
                result = subprocess.run(
                    [ffprobe, "-v", "quiet", "-print_format", "json",
                     "-show_format", audio_path],
                    capture_output=True, text=True, timeout=15,
                )
                if result.returncode == 0:
                    import json as _json
                    data = _json.loads(result.stdout)
                    return float(data["format"]["duration"])
        except Exception:
            pass

        # 兜底：按文件大小估算（MP3 192kbps ≈ 24000 bytes/sec）
        try:
            size = os.path.getsize(audio_path)
            return max(1.0, size / 24000)
        except Exception:
            return 10.0

    def _burn_subtitles(
        self,
        video_path: str,
        srt_path: str,
        output_path: str,
    ) -> bool:
        """
        使用 FFmpeg subtitles 滤镜将 SRT 字幕烧录进视频。

        字体大小和颜色由 settings.SUBTITLE_FONT_SIZE / SUBTITLE_FONT_COLOR 控制。
        烧录失败时静默返回 False（调用方保留原视频）。
        """
        font_size = getattr(settings, "SUBTITLE_FONT_SIZE", 36)
        font_color = getattr(settings, "SUBTITLE_FONT_COLOR", "white")

        # Windows 路径需将反斜杠转义，冒号用 \\: 转义
        srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")

        force_style = f"FontSize={font_size},PrimaryColour=&H00FFFFFF&"

        cmd = [
            self.ffmpeg_path, "-y",
            "-i", video_path,
            "-vf", f"subtitles='{srt_escaped}':force_style='{force_style}'",
            "-c:a", "copy",
            output_path,
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode != 0:
                logger.warning(f"字幕烧录失败: {result.stderr[-300:]}")
                return False
            logger.info(f"字幕烧录完成: {output_path}")
            return True
        except Exception as e:
            logger.warning(f"字幕烧录异常: {e}")
            return False

    def _generate_tts(self, text: str) -> Optional[str]:
        """
        生成 TTS 音频。
        使用的引擎由 settings.TTS_VOICE_NAME 前缀决定，默认 edge_tts（免费）。

        配置示例（.env）：
          TTS_VOICE_NAME=edge:zh-CN-XiaoxiaoNeural    # 默认，免费
          TTS_VOICE_NAME=siliconflow:anna             # 国内免费额度
          TTS_VOICE_NAME=azure:zh-CN-XiaoxiaoNeural  # 高质量付费
          TTS_VOICE_NAME=gemini:Zephyr
          TTS_VOICE_NAME=mimo:female_1
        """
        voice_name = getattr(settings, "TTS_VOICE_NAME", "edge:zh-CN-XiaoxiaoNeural")
        voice_rate = getattr(settings, "TTS_VOICE_RATE", 0)
        voice_volume = getattr(settings, "TTS_VOICE_VOLUME", 1.0)

        audio_path = os.path.join(self.temp_dir, f"tts_{abs(hash(text))}.mp3")

        logger.info(f"TTS 生成: engine={voice_name.split(':')[0]}, chars={len(text)}")
        ok = run_tts(
            text=text,
            voice_name=voice_name,
            output_file=audio_path,
            voice_rate=int(voice_rate),
            voice_volume=float(voice_volume),
        )
        if ok and os.path.exists(audio_path):
            return audio_path

        logger.warning("TTS 生成失败，视频将保留原始音频")
        return None

    def _combine_video_audio(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
    ) -> bool:
        """
        两阶段 FFmpeg 合成（移植自 MoneyPrinterTurbo）：
          阶段1: 提取原视频帧流（去除原音轨）
          阶段2: 将新 TTS 音频与视频流合并，时长以音频为准

        相比 MoviePy 合成：避免重新编码色彩损耗，性能更好。
        """
        with tempfile.TemporaryDirectory(dir=self.temp_dir) as tmp:
            silent_video = os.path.join(tmp, "silent.mp4")

            # 阶段1: 去除原音轨，保留视频流
            cmd_strip = [
                self.ffmpeg_path,
                "-y", "-i", video_path,
                "-an",                    # 移除音频
                "-c:v", "copy",           # 视频流直接复制，不重编码
                silent_video,
            ]
            r1 = subprocess.run(cmd_strip, capture_output=True, text=True, timeout=300)
            if r1.returncode != 0:
                logger.error(f"去除音轨失败: {r1.stderr[-500:]}")
                return False

            # 阶段2: 视频流 + 新音频合并，shortest 以较短的流为准
            cmd_merge = [
                self.ffmpeg_path,
                "-y",
                "-i", silent_video,
                "-i", audio_path,
                "-c:v", "copy",           # 视频流继续不重编码
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",              # 以音频时长为准截断视频
                output_path,
            ]
            r2 = subprocess.run(cmd_merge, capture_output=True, text=True, timeout=300)
            if r2.returncode != 0:
                logger.error(f"合成失败: {r2.stderr[-500:]}")
                return False

        logger.info(f"视频合成完成: {output_path}")
        return True

    def _extract_frames(self, video_path: str) -> str:
        """提取视频帧（用于后续逐帧处理，当前 _combine_video_audio 不需要此步骤）"""
        frames_dir = os.path.join(self.temp_dir, "frames")
        os.makedirs(frames_dir, exist_ok=True)

        cmd = [
            self.ffmpeg_path, "-y", "-i", video_path,
            "-vf", "fps=1",
            os.path.join(frames_dir, "frame_%04d.jpg"),
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=60)
        except Exception as e:
            logger.warning(f"提取帧失败: {e}")

        return frames_dir
