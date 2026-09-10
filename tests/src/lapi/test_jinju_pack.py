"""金句 pack：焊尾进三片；jinju/ 仅备选；无第四条。"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from lapi.deliver import pack_deliver  # noqa: E402
from lapi.jinju.pack import (  # noqa: E402
    pack_jinju,
    remove_legacy_preview_files,
    snapshot_narrative_bases,
)


def _fake_concat_run(cmd, check=True, capture_output=True):  # noqa: ANN001
    """模拟 ffmpeg concat：把 concat list 里的文件字节拼到输出。"""
    # cmd: ffmpeg -y -f concat -safe 0 -i list -c copy out
    list_path = Path(cmd[cmd.index("-i") + 1])
    out_path = Path(cmd[-1])
    parts: list[bytes] = []
    for line in list_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("file "):
            raw = line[5:].strip().strip("'")
            parts.append(Path(raw).read_bytes())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(b"".join(parts))
    return MagicMock(returncode=0)


class TestJinjuPack(unittest.TestCase):
    def test_pack_bakes_three_no_fourth(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            temp_dir = root / "temp" / "demo"
            out_dir = root / "output" / "demo"
            jinju = temp_dir / "jinju"
            jinju.mkdir(parents=True)
            out_dir.mkdir(parents=True)
            for name, body in (
                ("demo_特写_高光.mp4", b"N-C"),
                ("demo_全景_高光.mp4", b"N-W"),
                ("demo_混剪_高光.mp4", b"N-M"),
            ):
                (out_dir / name).write_bytes(body)
            (jinju / "candidates.json").write_text(
                '{"theme":"demo","recommended":0,"candidates":['
                '{"start":1.0,"end":3.5,"quote":"金句收尾","delivery":"punchy",'
                '"reason":"x","slug":"金句"}]}',
                encoding="utf-8",
            )
            (jinju / "axes.txt").write_text("closeup\t特写\tx\n", encoding="utf-8")
            (jinju / "review.md").write_text("# r\n", encoding="utf-8")
            (jinju / "00_金句_特写.mp4").write_bytes(b"+C")
            (jinju / "00_金句_全景.mp4").write_bytes(b"+W")
            (jinju / "demo_混剪_高光_含推荐收尾.mp4").write_bytes(b"LEGACY")
            (out_dir / "demo_混剪_高光_含推荐收尾.mp4").write_bytes(b"LEGACY")

            # timeline + transcript for srt append
            (temp_dir / "timeline.json").write_text(
                '{"theme":"demo","target_seconds":10,"audio_source":"closeup",'
                '"segments":[{"start":0,"end":5,"shot":"closeup","reason":"a"}]}',
                encoding="utf-8",
            )
            (temp_dir / "transcript.json").write_text(
                '{"text":"你好","words":[{"text":"你好","start":0.0,"end":1.0}]}',
                encoding="utf-8",
            )
            (temp_dir / "review_script.md").write_text("# r", encoding="utf-8")
            (temp_dir / "highlight.srt").write_text(
                "1\n00:00:00,000 --> 00:00:01,000\n你好\n", encoding="utf-8"
            )

            packed = pack_jinju(temp_dir, out_dir, run=_fake_concat_run)
            names = sorted(p.name for p in packed.iterdir())
            self.assertEqual(
                names,
                ["00_金句_全景.mp4", "00_金句_特写.mp4", "review.md"],
            )
            self.assertFalse((packed / "candidates.json").exists())
            self.assertFalse(
                (out_dir / "demo_混剪_高光_含推荐收尾.mp4").exists()
            )
            self.assertEqual((out_dir / "demo_特写_高光.mp4").read_bytes(), b"N-C+C")
            self.assertEqual((out_dir / "demo_全景_高光.mp4").read_bytes(), b"N-W+W")
            self.assertEqual((out_dir / "demo_混剪_高光.mp4").read_bytes(), b"N-M+C")
            # 二次 pack 不叠尾
            pack_jinju(temp_dir, out_dir, run=_fake_concat_run)
            self.assertEqual((out_dir / "demo_特写_高光.mp4").read_bytes(), b"N-C+C")
            v = (out_dir / "highlight_竖屏.srt").read_text(encoding="utf-8")
            h = (out_dir / "highlight_横屏.srt").read_text(encoding="utf-8")
            self.assertIn("金句收尾", v)
            self.assertIn("金句收尾", h)
            self.assertFalse((out_dir / "highlight.srt").exists())

    def test_dualcam_pack_preserves_jinju_no_fourth(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            temp_dir = root / "temp" / "demo"
            out_dir = root / "output" / "demo"
            temp_dir.mkdir(parents=True)
            out_dir.mkdir(parents=True)

            (temp_dir / "timeline.json").write_text("{}", encoding="utf-8")
            (temp_dir / "review_script.md").write_text("# r", encoding="utf-8")
            (temp_dir / "highlight_竖屏.srt").write_text("1\n", encoding="utf-8")
            (temp_dir / "highlight_横屏.srt").write_text("1\n", encoding="utf-8")
            for name in (
                "demo_特写_高光.mp4",
                "demo_全景_高光.mp4",
                "demo_混剪_高光.mp4",
            ):
                (out_dir / name).write_bytes(b"v")

            jinju = temp_dir / "jinju"
            jinju.mkdir()
            (jinju / "candidates.json").write_text(
                '{"theme":"demo","recommended":0,"candidates":['
                '{"start":1,"end":2,"quote":"金句","delivery":"falling","reason":"x"}]}',
                encoding="utf-8",
            )
            (jinju / "axes.txt").write_text("x\n", encoding="utf-8")
            (jinju / "review.md").write_text("# j\n", encoding="utf-8")
            (jinju / "00_金句_特写.mp4").write_bytes(b"s")
            (out_dir / "demo_混剪_高光_含推荐收尾.mp4").write_bytes(b"prev")

            packed = pack_deliver(temp_dir, out_dir, "demo")
            self.assertTrue((packed / "jinju" / "00_金句_特写.mp4").is_file())
            self.assertTrue((packed / "jinju" / "review.md").is_file())
            self.assertFalse((packed / "jinju" / "candidates.json").exists())
            self.assertFalse(
                (packed / "demo_混剪_高光_含推荐收尾.mp4").exists()
            )
            # dualcam pack 会重建 output，旧第四条不应被 restore 回来
            remove_legacy_preview_files(packed)
            self.assertFalse(
                any("含推荐收尾" in p.name for p in packed.iterdir())
            )

    def test_snapshot_narrative_force(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            temp_dir = root / "temp" / "demo"
            out_dir = root / "output" / "demo"
            temp_dir.mkdir(parents=True)
            out_dir.mkdir(parents=True)
            paths = {}
            for label, name in (
                ("closeup", "demo_特写_高光.mp4"),
                ("wide", "demo_全景_高光.mp4"),
                ("mix", "demo_混剪_高光.mp4"),
            ):
                p = out_dir / name
                p.write_bytes(b"new")
                paths[label] = p
            narr = snapshot_narrative_bases(
                "demo", temp_dir, video_paths=paths, force=True
            )
            self.assertEqual((narr / "demo_特写_高光.mp4").read_bytes(), b"new")


if __name__ == "__main__":
    unittest.main()
