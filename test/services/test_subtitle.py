"""
SubMaker 字幕时间轴单元测试

测试范围:
  mktimestamp:
    - 0 → "00:00:00,000"
    - 1 秒 (10_000_000 单位) → "00:00:01,000"
    - 1.5 秒 (15_000_000 单位) → "00:00:01,500"
    - 90 分钟 → "01:30:00,000"

  _ms_to_srt_timestamp:
    - 负数 → clamp to 0
    - 1234 ms → "00:00:01,234"

  SubMaker.from_timed_text:
    - 单句 → 1 条 cue
    - 多句按标点拆分
    - 最后一句拿剩余时间
    - 空文本 → 0 条 cue
    - 比例分配校验（前 N-1 句之和 = 最后句 start_ms）

  SubMaker.from_edge_tts_cues:
    - 空列表 → 0 条 cue
    - 词级 cues 聚合为句子
    - 句子结束标点触发 flush
    - 末尾无标点词被 flush 为最后一句

  SubMaker.to_srt:
    - 空 cues → 空字符串
    - 格式: index / timestamp line / text / 空行
    - 多条 cue 按 index 有序
    - --> 分隔符存在

  SubMaker.save_srt:
    - 创建文件
    - 文件内容 == to_srt()
    - UTF-8 BOM 编码（可被 utf-8-sig 解码）
"""

import os
from datetime import timedelta
from unittest.mock import MagicMock

import pytest


# ─── helpers ──────────────────────────────────────────────────────────────────

def _make_edge_cue(offset_ms: int, duration_ms: int, text: str):
    cue = MagicMock()
    cue.offset = timedelta(milliseconds=offset_ms)
    cue.duration = timedelta(milliseconds=duration_ms)
    cue.text = text
    return cue


# ═══════════════════════════════════════════════════════════════════════════════
# Section 1 — mktimestamp / _ms_to_srt_timestamp
# ═══════════════════════════════════════════════════════════════════════════════

class TestMkTimestamp:

    def test_zero(self):
        from app.services.subtitle.sub_maker import mktimestamp
        assert mktimestamp(0) == "00:00:00,000"

    def test_one_second(self):
        from app.services.subtitle.sub_maker import mktimestamp
        # 1 s = 10_000_000 × 100ns
        assert mktimestamp(10_000_000) == "00:00:01,000"

    def test_one_and_half_seconds(self):
        from app.services.subtitle.sub_maker import mktimestamp
        # 1.5 s = 15_000_000
        assert mktimestamp(15_000_000) == "00:00:01,500"

    def test_90_minutes(self):
        from app.services.subtitle.sub_maker import mktimestamp
        # 90 min = 5400 s = 54_000_000_000 × 100ns
        assert mktimestamp(54_000_000_000) == "01:30:00,000"

    def test_fractional_ms(self):
        from app.services.subtitle.sub_maker import mktimestamp
        # 1234 ms = 12_340_000 × 100ns
        assert mktimestamp(12_340_000) == "00:00:01,234"


class TestMsToSrtTimestamp:

    def test_negative_clamped_to_zero(self):
        from app.services.subtitle.sub_maker import _ms_to_srt_timestamp
        assert _ms_to_srt_timestamp(-100) == "00:00:00,000"

    def test_1234_ms(self):
        from app.services.subtitle.sub_maker import _ms_to_srt_timestamp
        assert _ms_to_srt_timestamp(1234) == "00:00:01,234"

    def test_3600000_ms_is_one_hour(self):
        from app.services.subtitle.sub_maker import _ms_to_srt_timestamp
        assert _ms_to_srt_timestamp(3_600_000) == "01:00:00,000"

    def test_comma_separator(self):
        from app.services.subtitle.sub_maker import _ms_to_srt_timestamp
        ts = _ms_to_srt_timestamp(500)
        assert "," in ts, "SRT 时间戳应使用逗号作为毫秒分隔符"


# ═══════════════════════════════════════════════════════════════════════════════
# Section 2 — SubMaker.from_timed_text
# ═══════════════════════════════════════════════════════════════════════════════

class TestFromTimedText:

    def test_empty_text_no_cues(self):
        from app.services.subtitle.sub_maker import SubMaker
        maker = SubMaker.from_timed_text("", 10.0)
        assert len(maker.cues) == 0

    def test_single_sentence(self):
        from app.services.subtitle.sub_maker import SubMaker
        maker = SubMaker.from_timed_text("这是一句话", 5.0)
        assert len(maker.cues) == 1
        assert maker.cues[0].start_ms == 0
        assert maker.cues[0].end_ms == 5000

    def test_multi_sentence_split_by_period(self):
        from app.services.subtitle.sub_maker import SubMaker
        text = "第一句。第二句。第三句"
        maker = SubMaker.from_timed_text(text, 9.0)
        assert len(maker.cues) == 3

    def test_last_sentence_gets_remaining_time(self):
        from app.services.subtitle.sub_maker import SubMaker
        text = "开头。结尾"
        maker = SubMaker.from_timed_text(text, 10.0)
        last = maker.cues[-1]
        assert last.end_ms == 10_000

    def test_cues_contiguous(self):
        """每个 cue 的 end_ms 等于下一个 cue 的 start_ms。"""
        from app.services.subtitle.sub_maker import SubMaker
        text = "A句。B句。C句"
        maker = SubMaker.from_timed_text(text, 12.0)
        for i in range(len(maker.cues) - 1):
            assert maker.cues[i].end_ms == maker.cues[i + 1].start_ms

    def test_indices_sequential(self):
        from app.services.subtitle.sub_maker import SubMaker
        maker = SubMaker.from_timed_text("句A。句B。句C", 6.0)
        for i, cue in enumerate(maker.cues, start=1):
            assert cue.index == i

    def test_proportional_timing(self):
        """字符多的句子获得更多时间。"""
        from app.services.subtitle.sub_maker import SubMaker
        short = "短。"
        long_text = "这是一个比较长的句子内容会占据更多时间"
        text = short + long_text
        maker = SubMaker.from_timed_text(text, 20.0)
        assert len(maker.cues) == 2
        assert maker.cues[1].end_ms - maker.cues[1].start_ms > \
               maker.cues[0].end_ms - maker.cues[0].start_ms


# ═══════════════════════════════════════════════════════════════════════════════
# Section 3 — SubMaker.from_edge_tts_cues
# ═══════════════════════════════════════════════════════════════════════════════

class TestFromEdgeTTSCues:

    def test_empty_cues(self):
        from app.services.subtitle.sub_maker import SubMaker
        maker = SubMaker.from_edge_tts_cues([])
        assert len(maker.cues) == 0

    def test_words_aggregated_to_sentence(self):
        """多个词级 cue 聚合为一条句子字幕。"""
        from app.services.subtitle.sub_maker import SubMaker
        cues = [
            _make_edge_cue(0, 300, "你好"),
            _make_edge_cue(300, 300, "世界"),
            _make_edge_cue(600, 300, "！"),
        ]
        maker = SubMaker.from_edge_tts_cues(cues)
        assert len(maker.cues) == 1
        assert "你好" in maker.cues[0].text
        assert maker.cues[0].start_ms == 0
        assert maker.cues[0].end_ms == 900

    def test_sentence_boundary_triggers_flush(self):
        """句子结束标点后的词语应从新句子开始。"""
        from app.services.subtitle.sub_maker import SubMaker
        cues = [
            _make_edge_cue(0,    400, "第一句"),
            _make_edge_cue(400,  200, "。"),
            _make_edge_cue(600,  400, "第二句"),
            _make_edge_cue(1000, 200, "！"),
        ]
        maker = SubMaker.from_edge_tts_cues(cues)
        assert len(maker.cues) == 2

    def test_trailing_words_flushed(self):
        """末尾无标点词语被收集为最后一条字幕。"""
        from app.services.subtitle.sub_maker import SubMaker
        cues = [
            _make_edge_cue(0,   300, "第一句。"),
            _make_edge_cue(300, 300, "尾巴词"),
        ]
        maker = SubMaker.from_edge_tts_cues(cues)
        assert len(maker.cues) == 2
        assert "尾巴词" in maker.cues[1].text

    def test_start_end_ms_from_timedelta(self):
        from app.services.subtitle.sub_maker import SubMaker
        cues = [_make_edge_cue(1500, 500, "词语。")]
        maker = SubMaker.from_edge_tts_cues(cues)
        assert maker.cues[0].start_ms == 1500
        assert maker.cues[0].end_ms == 2000


# ═══════════════════════════════════════════════════════════════════════════════
# Section 4 — SubMaker.to_srt
# ═══════════════════════════════════════════════════════════════════════════════

class TestToSRT:

    def test_empty_returns_empty_string(self):
        from app.services.subtitle.sub_maker import SubMaker
        maker = SubMaker([])
        assert maker.to_srt() == ""

    def test_single_cue_format(self):
        from app.services.subtitle.sub_maker import SubMaker, SubtitleCue
        maker = SubMaker([SubtitleCue(index=1, start_ms=0, end_ms=2000, text="Hello")])
        srt = maker.to_srt()
        lines = srt.split("\n")
        assert lines[0] == "1"
        assert "00:00:00,000 --> 00:00:02,000" in lines[1]
        assert lines[2] == "Hello"
        assert lines[3] == ""

    def test_arrow_separator_present(self):
        from app.services.subtitle.sub_maker import SubMaker, SubtitleCue
        maker = SubMaker([SubtitleCue(1, 0, 1000, "T")])
        assert "-->" in maker.to_srt()

    def test_multiple_cues_all_present(self):
        from app.services.subtitle.sub_maker import SubMaker, SubtitleCue
        cues = [
            SubtitleCue(1, 0, 1000, "First"),
            SubtitleCue(2, 1000, 2000, "Second"),
            SubtitleCue(3, 2000, 3000, "Third"),
        ]
        srt = SubMaker(cues).to_srt()
        assert "First" in srt
        assert "Second" in srt
        assert "Third" in srt
        assert srt.index("First") < srt.index("Second") < srt.index("Third")

    def test_srt_from_timed_text_roundtrip(self):
        from app.services.subtitle.sub_maker import SubMaker
        maker = SubMaker.from_timed_text("第一句话。第二句话", 6.0)
        srt = maker.to_srt()
        assert "1" in srt
        assert "2" in srt
        assert "-->" in srt


# ═══════════════════════════════════════════════════════════════════════════════
# Section 5 — SubMaker.save_srt
# ═══════════════════════════════════════════════════════════════════════════════

class TestSaveSRT:

    def test_save_creates_file(self, tmp_path):
        from app.services.subtitle.sub_maker import SubMaker
        maker = SubMaker.from_timed_text("测试文本", 3.0)
        path = str(tmp_path / "sub.srt")
        maker.save_srt(path)
        assert os.path.exists(path)

    def test_file_content_matches_to_srt(self, tmp_path):
        from app.services.subtitle.sub_maker import SubMaker
        maker = SubMaker.from_timed_text("你好世界。再见朋友", 4.0)
        path = str(tmp_path / "sub.srt")
        maker.save_srt(path)
        with open(path, encoding="utf-8-sig") as f:
            content = f.read()
        assert content == maker.to_srt()

    def test_utf8_bom_encoding(self, tmp_path):
        """文件应以 UTF-8 BOM 开头，兼容 Windows 播放器。"""
        from app.services.subtitle.sub_maker import SubMaker
        maker = SubMaker.from_timed_text("中文字幕", 2.0)
        path = str(tmp_path / "sub.srt")
        maker.save_srt(path)
        with open(path, "rb") as f:
            raw = f.read(3)
        assert raw == b"\xef\xbb\xbf", "文件应以 UTF-8 BOM (EF BB BF) 开头"

    def test_empty_cues_saves_empty_file(self, tmp_path):
        from app.services.subtitle.sub_maker import SubMaker
        maker = SubMaker([])
        path = str(tmp_path / "empty.srt")
        maker.save_srt(path)
        with open(path, encoding="utf-8-sig") as f:
            content = f.read()
        assert content == ""
