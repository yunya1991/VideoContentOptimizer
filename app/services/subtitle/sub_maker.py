"""
字幕时间轴抽象 — SubMaker
移植自 MoneyPrinterTurbo app/utils/utils.py + app/services/voice.py

功能:
  - 从 edge_tts 7.x SubMaker.cues（timedelta）构建字幕
  - 从文本 + 音频时长按字符比例构建字幕
  - 生成标准 SRT 格式字幕
  - 保存到文件（UTF-8 BOM）
"""

import re
from dataclasses import dataclass
from typing import List, Optional

# 用于句子分割的标点符号集（中英文）
_SENTENCE_END_RE = re.compile(r"[。！？!?；;…]+")
_SPLIT_RE = re.compile(r"[。！？!?；;…,，.]+")


@dataclass
class SubtitleCue:
    """单条字幕条目"""
    index: int
    start_ms: int   # 毫秒
    end_ms: int     # 毫秒
    text: str


def _ms_to_srt_timestamp(ms: int) -> str:
    """毫秒 → SRT 时间戳 'HH:MM:SS,mmm'"""
    ms = max(0, ms)
    hours = ms // 3_600_000
    ms %= 3_600_000
    minutes = ms // 60_000
    ms %= 60_000
    seconds = ms // 1_000
    milliseconds = ms % 1_000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def mktimestamp(time_unit_100ns: float) -> str:
    """
    100 纳秒单位时间 → SRT 时间戳 'HH:MM:SS,mmm'

    兼容 edge_tts WordBoundary 事件的 offset 字段（整数 100ns 单位）。
    """
    ms = int(time_unit_100ns / 10_000)
    return _ms_to_srt_timestamp(ms)


def _split_by_punctuation(text: str) -> List[str]:
    """按中英文句子标点拆分文本，过滤空片段。"""
    parts = _SPLIT_RE.split(text)
    return [p.strip() for p in parts if p.strip()]


class SubMaker:
    """
    字幕时间轴管理器。

    构建方式::

        # edge_tts 7.x 词边界 cues
        maker = SubMaker.from_edge_tts_cues(edge_sub_maker.cues)

        # 按字符比例分配（任意 TTS 引擎）
        maker = SubMaker.from_timed_text(script_text, audio_duration_seconds=12.5)

    输出::

        srt_text = maker.to_srt()
        maker.save_srt("/tmp/output.srt")
    """

    def __init__(self, cues: List[SubtitleCue]):
        self.cues = cues

    # ─── 工厂方法 ──────────────────────────────────────────────────────────

    @classmethod
    def from_edge_tts_cues(cls, edge_cues) -> "SubMaker":
        """
        从 edge_tts 7.x SubMaker.cues 构建字幕。

        每个 cue 具有:
          offset   : timedelta — 词起始时间
          duration : timedelta — 词持续时间
          text     : str       — 词文本（也可能是 word 属性）

        词级 cues 被聚合为句子级字幕：遇到句子结束标点时 flush。
        """
        if not edge_cues:
            return cls([])

        sentences: List[SubtitleCue] = []
        buf_words: List[str] = []
        buf_start_ms: Optional[int] = None
        buf_end_ms: int = 0
        idx = 1

        for cue in edge_cues:
            start_ms = int(cue.offset.total_seconds() * 1000)
            end_ms = int((cue.offset + cue.duration).total_seconds() * 1000)
            word = getattr(cue, "text", getattr(cue, "word", ""))

            if buf_start_ms is None:
                buf_start_ms = start_ms
            buf_end_ms = end_ms
            buf_words.append(word)

            if _SENTENCE_END_RE.search(word):
                text = "".join(buf_words).strip()
                if text:
                    sentences.append(SubtitleCue(
                        index=idx, start_ms=buf_start_ms,
                        end_ms=buf_end_ms, text=text,
                    ))
                    idx += 1
                buf_words = []
                buf_start_ms = None

        # flush 末尾未结束的句子
        if buf_words and buf_start_ms is not None:
            text = "".join(buf_words).strip()
            if text:
                sentences.append(SubtitleCue(
                    index=idx, start_ms=buf_start_ms,
                    end_ms=buf_end_ms, text=text,
                ))

        return cls(sentences)

    @classmethod
    def from_timed_text(cls, text: str, audio_duration_seconds: float) -> "SubMaker":
        """
        按字符比例分配时间轴（适用于无词边界信息的 TTS 引擎）。

        最后一个句子获得剩余全部时间，其余按字符数比例分配。
        """
        sentences = _split_by_punctuation(text)
        if not sentences:
            return cls([])

        total_chars = sum(len(s) for s in sentences) or 1
        total_ms = int(audio_duration_seconds * 1000)

        cues: List[SubtitleCue] = []
        cursor_ms = 0

        for idx, sentence in enumerate(sentences, start=1):
            is_last = (idx == len(sentences))
            if is_last:
                end_ms = total_ms
            else:
                end_ms = cursor_ms + int(total_ms * len(sentence) / total_chars)

            cues.append(SubtitleCue(
                index=idx,
                start_ms=cursor_ms,
                end_ms=end_ms,
                text=sentence,
            ))
            cursor_ms = end_ms

        return cls(cues)

    # ─── 输出方法 ──────────────────────────────────────────────────────────

    def to_srt(self) -> str:
        """生成 SRT 格式字幕字符串。"""
        if not self.cues:
            return ""

        lines: List[str] = []
        for cue in self.cues:
            lines.append(str(cue.index))
            lines.append(
                f"{_ms_to_srt_timestamp(cue.start_ms)} --> {_ms_to_srt_timestamp(cue.end_ms)}"
            )
            lines.append(cue.text)
            lines.append("")

        return "\n".join(lines)

    def save_srt(self, path: str) -> None:
        """将 SRT 字幕写入文件（UTF-8 BOM，兼容部分播放器）。"""
        with open(path, "w", encoding="utf-8-sig") as f:
            f.write(self.to_srt())
