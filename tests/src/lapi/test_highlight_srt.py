"""高光成片轴字幕：词级时间映射；横竖屏由 captions 写出。"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from lapi.highlight_srt import (  # noqa: E402
    map_words_to_highlight_timeline,
    timeline_to_highlight_srt,
    write_highlight_srt,
)
from lapi.timeline import Segment, Timeline  # noqa: E402


class TestHighlightSrt(unittest.TestCase):
    def test_map_words_composed_axis_starts_at_zero(self) -> None:
        timeline = Timeline(
            target_seconds=20,
            audio_source="closeup",
            segments=[
                Segment(start=100.0, end=103.0, shot="closeup", reason="a"),
                Segment(start=200.0, end=202.0, shot="wide", reason="b"),
            ],
            theme="t",
        )
        words = [
            {"text": "甲", "start": 100.0, "end": 100.5},
            {"text": "乙", "start": 101.0, "end": 101.5},
            {"text": "丙", "start": 200.2, "end": 200.8},
            {"text": "丁", "start": 150.0, "end": 150.5},  # 不在任何段
        ]
        mapped = map_words_to_highlight_timeline(words, timeline)
        self.assertEqual([w["text"] for w in mapped], ["甲", "乙", "丙"])
        self.assertAlmostEqual(mapped[0]["start"], 0.0)
        self.assertAlmostEqual(mapped[0]["end"], 0.5)
        self.assertAlmostEqual(mapped[1]["start"], 1.0)
        self.assertAlmostEqual(mapped[1]["end"], 1.5)
        # 第二段：源 200.2 → 成片 3.0 + 0.2 = 3.2
        self.assertAlmostEqual(mapped[2]["start"], 3.2)
        self.assertAlmostEqual(mapped[2]["end"], 3.8)

    def test_srt_contains_composed_timestamps(self) -> None:
        timeline = Timeline(
            target_seconds=10,
            audio_source="closeup",
            segments=[Segment(start=50.0, end=52.0, shot="closeup")],
            theme="t",
        )
        words = [
            {"text": "你好。", "start": 50.0, "end": 51.0},
            {"text": "世界", "start": 51.2, "end": 51.8},
        ]
        srt = timeline_to_highlight_srt(timeline, words)
        self.assertIn("00:00:00,000 -->", srt)
        self.assertIn("你好", srt)
        self.assertNotIn("你好。", srt)  # 断句符→空格后去掉
        self.assertNotIn("00:00:50", srt)

    def test_write_highlight_srt_writes_vertical(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            timeline = Timeline(
                target_seconds=5,
                audio_source="closeup",
                segments=[Segment(start=10.0, end=11.0, shot="closeup")],
                theme="demo",
            )
            timeline.save(temp / "timeline.json")
            (temp / "transcript.json").write_text(
                json.dumps(
                    {"text": "测", "words": [{"text": "测", "start": 10.0, "end": 10.5}]},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            path = write_highlight_srt(temp)
            self.assertEqual(path.name, "highlight_竖屏.srt")
            self.assertTrue((temp / "highlight_横屏.srt").is_file())
            self.assertFalse((temp / "highlight.srt").exists())
            body = path.read_text(encoding="utf-8")
            self.assertIn("测", body)
            self.assertIn("00:00:00,000", body)


if __name__ == "__main__":
    unittest.main()
