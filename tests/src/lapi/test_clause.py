"""小句补全与叠词单测。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from lapi.director.auto import complete_clause  # noqa: E402
from lapi.director.fillers import cut_fillers  # noqa: E402
from lapi.director.prompts_loader import (  # noqa: E402
    load_filler_config,
    load_selection_config,
)
from lapi.director.shots import plan_shots  # noqa: E402
from lapi.director.prompts_loader import load_shot_config  # noqa: E402


def _w(text: str, start: float, dur: float = 0.35) -> dict:
    return {"text": text, "start": start, "end": start + dur}


class TestCompleteClause(unittest.TestCase):
    def test_extends_to_finish_dong_yewu(self) -> None:
        # 模拟截在「叫做懂」——应扩到「业务」后停顿
        words = []
        t = 100.0
        for tok in ["就", "这", "句", "话", "叫做", "懂", "业务", "的", "人"]:
            words.append(_w(tok, t, 0.4))
            t += 0.45
        # 大停顿后再说话
        t += 0.8
        words.append(_w("另外", t, 0.4))

        cfg = load_selection_config()
        # 故意截在「懂」结束
        start = words[0]["start"]
        end = words[5]["end"]  # 懂
        ns, ne, text = complete_clause(words, start, end, cfg)
        self.assertIn("懂业务", text)
        self.assertGreater(ne, end)


class TestStutter(unittest.TestCase):
    def test_cuts_wo_wo_wo(self) -> None:
        cfg = load_filler_config()
        words = [
            _w("就是", 0.0),
            _w("我", 0.4),
            _w("我", 0.7),
            _w("我", 1.0),
            _w("觉得", 1.3),
            _w("好", 1.7),
        ]
        keeps, n, _ = cut_fillers(words, 0.0, 2.2, cfg)
        text = "".join(
            w["text"]
            for a, b in keeps
            for w in words
            if w["start"] >= a - 0.05 and w["end"] <= b + 0.05
        )
        self.assertLessEqual(text.count("我"), 1)
        self.assertIn("觉得", text)
        self.assertGreaterEqual(n, 1)

    def test_cuts_stutter_with_commas(self) -> None:
        """STT 常把「我，我，我觉得」拆成 我 + ， + 我 + ， + 我 + 觉 + 得。"""
        cfg = load_filler_config()
        words = [
            _w("，", 0.0, 0.1),
            _w("我", 0.2, 0.15),
            _w("，", 0.35, 0.1),
            _w("我", 0.5, 0.15),
            _w("，", 0.65, 0.1),
            _w("我", 0.8, 0.15),
            _w("觉", 1.0, 0.15),
            _w("得", 1.2, 0.15),
            _w("好", 1.5, 0.2),
        ]
        keeps, n, _ = cut_fillers(words, 0.0, 2.0, cfg)
        text = "".join(
            w["text"]
            for a, b in keeps
            for w in words
            if w["start"] >= a - 0.05 and w["end"] <= b + 0.05
        )
        self.assertLessEqual(text.count("我"), 1)
        self.assertIn("觉得", text.replace("觉", "觉").replace("得", "得"))
        self.assertIn("觉", text)
        self.assertIn("得", text)
        self.assertGreaterEqual(n, 1)


class TestShotsPauseOnly(unittest.TestCase):
    def test_no_mid_phrase_establish_without_pause(self) -> None:
        cfg = load_shot_config()
        # 连续说话无大停顿 → 整段一镜
        words = [_w(f"词{i}", i * 0.4, 0.35) for i in range(30)]
        segs = plan_shots(
            [(0.0, 12.0)],
            "FDE 流程革命",
            reason="主题",
            shot_cfg=cfg,
            beat_index=0,
            words=words,
            pause_gap=0.6,
        )
        self.assertEqual(len(segs), 1)
        self.assertEqual(segs[0].shot, "closeup")

    def test_split_only_at_pause(self) -> None:
        cfg = load_shot_config()
        words = []
        t = 0.0
        for i in range(10):
            words.append(_w(f"前{i}", t, 0.35))
            t += 0.4
        t += 0.7  # 停顿
        pause_at = t
        for i in range(20):
            words.append(_w(f"后{i}", t, 0.35))
            t += 0.4
        segs = plan_shots(
            [(0.0, t)],
            "FDE OPC",
            reason="主题",
            shot_cfg=cfg,
            beat_index=0,
            words=words,
            pause_gap=0.6,
        )
        if len(segs) > 1:
            for a, b in zip(segs, segs[1:]):
                self.assertAlmostEqual(a.end, b.start, places=2)
            # 切点应靠近停顿
            self.assertAlmostEqual(segs[0].end, pause_at, delta=0.15)


if __name__ == "__main__":
    unittest.main()
