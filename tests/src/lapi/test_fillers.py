"""语气词快剪单测。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from lapi.director.fillers import cut_fillers  # noqa: E402
from lapi.director.prompts_loader import load_filler_config  # noqa: E402


def _w(text: str, start: float, dur: float = 0.3) -> dict:
    return {"text": text, "start": start, "end": start + dur}


class TestFillers(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = load_filler_config()

    def test_cuts_standalone_fillers(self) -> None:
        words = [
            _w("我们", 0.0),
            _w("呃", 0.4),
            _w("需要", 0.8),
            _w("那个", 1.2),
            _w("FDE", 1.6),
        ]
        keeps, n, sec = cut_fillers(words, 0.0, 2.2, self.cfg)
        self.assertGreater(n, 0)
        self.assertGreater(sec, 0)
        joined = []
        for a, b in keeps:
            joined.extend(
                w["text"] for w in words if w["start"] >= a - 0.05 and w["end"] <= b + 0.05
            )
        self.assertIn("FDE", "".join(joined))
        self.assertNotIn("呃", "".join(joined))

    def test_protect_demonstrative_plus_noun(self) -> None:
        words = [
            _w("看看", 0.0),
            _w("这个", 0.4),
            _w("产品", 0.8),
            _w("很好", 1.2),
        ]
        keeps, n, _ = cut_fillers(words, 0.0, 1.8, self.cfg)
        text = "".join(
            w["text"]
            for a, b in keeps
            for w in words
            if w["start"] >= a - 0.05 and w["end"] <= b + 0.05
        )
        self.assertIn("这个产品", text)
        self.assertEqual(n, 0)

    def test_keep_then_we_start(self) -> None:
        words = [
            _w("好", 0.0),
            _w("然后", 0.4),
            _w("我们", 0.8),
            _w("开始", 1.2),
            _w("做", 1.6),
        ]
        keeps, n, _ = cut_fillers(words, 0.0, 2.2, self.cfg)
        text = "".join(
            w["text"]
            for a, b in keeps
            for w in words
            if w["start"] >= a - 0.05 and w["end"] <= b + 0.05
        )
        self.assertIn("然后我们", text)

    def test_min_keep_not_shatter(self) -> None:
        words = [
            _w("A", 0.0, 0.2),
            _w("呃", 0.25, 0.15),
            _w("B词够长", 0.5, 0.8),
        ]
        keeps, _, _ = cut_fillers(words, 0.0, 1.5, self.cfg)
        for a, b in keeps:
            self.assertGreaterEqual(b - a, 0.2)


if __name__ == "__main__":
    unittest.main()
