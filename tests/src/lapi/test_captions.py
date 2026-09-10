"""横竖屏字幕：断句符→空格；计字不计空格；词边界切 cue。"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from lapi.captions.format import (  # noqa: E402
    display_len,
    format_quote_as_cues,
    pack_words_to_cues,
    replace_break_punct_with_space,
)
from lapi.captions.write import write_caption_set  # noqa: E402
from lapi.timeline import Segment, Timeline  # noqa: E402


class TestCaptionsFormat(unittest.TestCase):
    def test_break_punct_to_space_keeps_quotes(self) -> None:
        s = replace_break_punct_with_space("真正AI，要落地！「组织」问题。")
        self.assertEqual(s, "真正AI 要落地 「组织」问题")
        self.assertEqual(display_len(s), display_len("真正AI要落地「组织」问题"))

    def test_pack_respects_max_chars_word_boundary(self) -> None:
        words = [
            {"text": "一二三四五六七", "start": 0.0, "end": 1.0},
            {"text": "八九十", "start": 1.0, "end": 2.0},
            {"text": "十一十二", "start": 2.0, "end": 3.0},
        ]
        cues = pack_words_to_cues(words, max_chars=14)
        # 7+3=10 ≤14；再加 4 →14，可同 cue；超则拆
        self.assertTrue(all(display_len(t) <= 14 for _, _, t in cues))
        self.assertEqual("".join(t.replace(" ", "") for _, _, t in cues), "一二三四五六七八九十十一十二")

    def test_format_quote_splits_by_profile(self) -> None:
        cues = format_quote_as_cues(
            "真正 AI 要落地，它其实不仅仅是个 AI 问题，它是个组织问题",
            65.0,
            69.0,
            max_chars=14,
        )
        self.assertTrue(len(cues) >= 2)
        self.assertTrue(all(display_len(t) <= 14 for _, _, t in cues))
        self.assertAlmostEqual(cues[0][0], 65.0)
        self.assertAlmostEqual(cues[-1][1], 69.0)
        joined = " ".join(t for _, _, t in cues)
        self.assertNotIn("，", joined)
        self.assertIn("组织问题", joined)


class TestWriteCaptionSet(unittest.TestCase):
    def test_writes_both_and_removes_legacy(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            Timeline(
                target_seconds=5,
                audio_source="closeup",
                segments=[Segment(start=0.0, end=2.0, shot="closeup")],
                theme="demo",
            ).save(temp / "timeline.json")
            (temp / "transcript.json").write_text(
                json.dumps(
                    {
                        "text": "你好世界",
                        "words": [
                            {"text": "你好，", "start": 0.0, "end": 0.5},
                            {"text": "世界", "start": 0.6, "end": 1.0},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (temp / "highlight.srt").write_text("legacy\n", encoding="utf-8")
            out = temp / "out"
            written = write_caption_set(
                temp,
                output_dir=out,
                jinju_quote="收尾金句！",
                jinju_start=2.0,
                jinju_end=4.0,
            )
            self.assertTrue(written["竖屏"].is_file())
            self.assertTrue(written["横屏"].is_file())
            self.assertFalse((temp / "highlight.srt").exists())
            self.assertFalse((out / "highlight.srt").exists())
            body = written["竖屏"].read_text(encoding="utf-8")
            self.assertIn("你好", body)
            self.assertNotIn("你好，", body)
            self.assertIn("收尾金句", body)
            self.assertIn("00:00:02,000", body)


if __name__ == "__main__":
    unittest.main()
