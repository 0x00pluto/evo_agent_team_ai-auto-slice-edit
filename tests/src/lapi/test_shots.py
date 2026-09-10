"""镜头语言展开单测。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from lapi.director.prompts_loader import load_shot_config  # noqa: E402
from lapi.director.shots import plan_shots  # noqa: E402


class TestShots(unittest.TestCase):
    def test_splits_long_keep_into_shots(self) -> None:
        cfg = load_shot_config()
        # 带停顿的长保留片才切镜
        words = []
        t = 100.0
        for i in range(8):
            words.append({"text": f"a{i}", "start": t, "end": t + 0.35})
            t += 0.4
        t += 0.7
        for i in range(20):
            words.append({"text": f"b{i}", "start": t, "end": t + 0.35})
            t += 0.4
        segs = plan_shots(
            [(100.0, t)],
            "我们要招 FDE 和 OPC 做流程革命",
            reason="主题",
            shot_cfg=cfg,
            beat_index=0,
            words=words,
            pause_gap=0.6,
        )
        self.assertGreaterEqual(len(segs), 1)
        self.assertAlmostEqual(segs[0].start, 100.0, places=2)
        self.assertAlmostEqual(segs[-1].end, t, places=2)
        for a, b in zip(segs, segs[1:]):
            self.assertLessEqual(a.end, b.start + 1e-6)
        self.assertTrue(any(s.shot == "closeup" for s in segs))

    def test_theme_prefers_closeup(self) -> None:
        cfg = load_shot_config()
        segs = plan_shots(
            [(0.0, 6.0)],
            "FDE 才是核心",
            reason="主题",
            shot_cfg=cfg,
            beat_index=1,
        )
        self.assertTrue(any(s.shot == "closeup" for s in segs))

    def test_long_non_theme_can_insert_wide(self) -> None:
        """有停顿的长段应能在定场/换气处出现全景（不再恒特写）。"""
        cfg = load_shot_config()
        words = []
        t = 100.0
        for i in range(8):
            words.append({"text": f"a{i}", "start": t, "end": t + 0.35})
            t += 0.4
        t += 0.7  # 停顿，可供定场切开
        for i in range(25):
            words.append({"text": f"b{i}", "start": t, "end": t + 0.35})
            t += 0.4
        segs = plan_shots(
            [(100.0, t)],
            "我们今天随便聊聊天气和日常安排",
            reason="非主题",
            shot_cfg=cfg,
            beat_index=0,
            words=words,
            pause_gap=0.6,
        )
        self.assertTrue(any(s.shot == "wide" for s in segs))
        self.assertTrue(any(s.shot == "closeup" for s in segs))


if __name__ == "__main__":
    unittest.main()
