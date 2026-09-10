"""导演选段与 prompts 加载单测。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from lapi.director.auto import direct_auto  # noqa: E402
from lapi.director.prompts_loader import (  # noqa: E402
    load_prompt_text,
    load_selection_config,
    load_shot_config,
    parse_kv_config,
)
from lapi.director.review import render_review_script  # noqa: E402


def _fake_transcript(duration: float = 600.0) -> dict:
    """生成约 duration 秒、有停顿的假转写。"""
    words = []
    t = 0.0
    i = 0
    while t < duration:
        # 每句约 12 秒说话 + 1 秒停顿
        for j in range(24):
            words.append(
                {
                    "text": f"词{i}",
                    "start": t,
                    "end": t + 0.45,
                }
            )
            t += 0.5
            i += 1
        t += 1.0  # pause
        # 塞一点高信息词
        if i % 100 < 24:
            words[-1]["text"] = "核心"
    return {"text": "".join(w["text"] for w in words), "words": words}


class TestDirector(unittest.TestCase):
    def test_prompts_loadable(self) -> None:
        self.assertIn("导演", load_prompt_text("system.md"))
        cfg = load_selection_config()
        self.assertIn("target_tolerance_seconds", cfg)
        scfg = load_shot_config()
        self.assertTrue(scfg.get("wide_keywords"))

    def test_parse_kv(self) -> None:
        text = "pause_gap_seconds: 0.6\nwide_keywords: 有请,欢迎\n"
        cfg = parse_kv_config(text)
        self.assertEqual(cfg["pause_gap_seconds"], 0.6)
        self.assertEqual(cfg["wide_keywords"], ["有请", "欢迎"])

    def test_direct_auto_budget(self) -> None:
        tl = direct_auto(_fake_transcript(600), target_seconds=120, theme="t")
        self.assertGreater(len(tl.segments), 0)
        total = tl.total_duration()
        self.assertGreaterEqual(total, 40)
        self.assertLessEqual(total, 160)
        for a, b in zip(tl.segments, tl.segments[1:]):
            self.assertLessEqual(a.end, b.start + 1e-6)
        for s in tl.segments:
            self.assertIn(s.shot, ("wide", "closeup"))
        # 收紧后单段不应普遍接近旧的 28s
        avg = total / max(len(tl.segments), 1)
        self.assertLessEqual(avg, 18.0)

    def test_theme_keywords_boost_fde_opc(self) -> None:
        words = []
        t = 50.0
        # filler dense chunk without theme
        for i in range(30):
            words.append({"text": f"闲聊{i}", "start": t, "end": t + 0.4})
            t += 0.45
        t += 2.0
        theme_start = t
        for i, tok in enumerate(
            ["我们", "要", "招", "FDE", "和", "OPC", "做", "流程革命", "与", "组织提效"]
        ):
            words.append({"text": tok, "start": t, "end": t + 0.8})
            t += 0.85
        theme_end = t
        # pad theme chunk to >= min_segment
        while theme_end - theme_start < 10:
            words.append({"text": "补", "start": t, "end": t + 0.5})
            t += 0.55
            theme_end = t

        tr = {"text": "".join(w["text"] for w in words), "words": words}
        tl = direct_auto(tr, target_seconds=20, theme="demo")
        joined = " ".join(
            "".join(
                w["text"]
                for w in words
                if w["start"] >= s.start - 0.01 and w["end"] <= s.end + 0.01
            )
            for s in tl.segments
        )
        self.assertTrue(
            any(k in joined for k in ("FDE", "OPC", "流程革命")),
            f"应优先峰会主题段，实际: {joined!r} reasons={[s.reason for s in tl.segments]}",
        )

    def test_review_script(self) -> None:
        tr = _fake_transcript(200)
        tl = direct_auto(tr, target_seconds=60, theme="demo")
        md = render_review_script(tl, tr["words"], theme="demo")
        self.assertIn("拉片审阅稿", md)
        self.assertIn("口播摘录", md)



if __name__ == "__main__":
    unittest.main()
