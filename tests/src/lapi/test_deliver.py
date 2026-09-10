"""交付包组装：output 只含清单，不含 transcript/sources/timeline。"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from lapi.deliver import pack_deliver  # noqa: E402


class TestPackDeliver(unittest.TestCase):
    def test_pack_keeps_only_deliverables(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            temp_dir = root / "temp" / "demo"
            out_dir = root / "output" / "demo"
            temp_dir.mkdir(parents=True)
            out_dir.mkdir(parents=True)

            (temp_dir / "timeline.json").write_text('{"ok":1}', encoding="utf-8")
            (temp_dir / "review_script.md").write_text("# r", encoding="utf-8")
            (temp_dir / "highlight_竖屏.srt").write_text(
                "1\n00:00:00,000 --> 00:00:01,000\n你好\n", encoding="utf-8"
            )
            (temp_dir / "highlight_横屏.srt").write_text(
                "1\n00:00:00,000 --> 00:00:01,000\n你好\n", encoding="utf-8"
            )
            (temp_dir / "transcript.json").write_text("{}", encoding="utf-8")
            (temp_dir / "sources.json").write_text("{}", encoding="utf-8")

            for name in (
                "demo_特写_高光.mp4",
                "demo_全景_高光.mp4",
                "demo_混剪_高光.mp4",
            ):
                (out_dir / name).write_bytes(b"fake-mp4")
            # 污染：工作文件误落在 output
            (out_dir / "transcript.json").write_text("leak", encoding="utf-8")
            (out_dir / "sources.json").write_text("leak", encoding="utf-8")
            (out_dir / "timeline.json").write_text("leak", encoding="utf-8")

            packed = pack_deliver(temp_dir, out_dir, "demo")
            names = sorted(p.name for p in packed.iterdir())
            self.assertEqual(
                names,
                [
                    "demo_全景_高光.mp4",
                    "demo_混剪_高光.mp4",
                    "demo_特写_高光.mp4",
                    "highlight_横屏.srt",
                    "highlight_竖屏.srt",
                    "review_script.md",
                ],
            )
            self.assertNotIn("transcript.json", names)
            self.assertNotIn("sources.json", names)
            self.assertNotIn("timeline.json", names)
            self.assertEqual(
                (packed / "review_script.md").read_text(encoding="utf-8"), "# r"
            )

    def test_pack_missing_doc_raises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            temp_dir = root / "temp" / "demo"
            out_dir = root / "output" / "demo"
            temp_dir.mkdir(parents=True)
            out_dir.mkdir(parents=True)
            (temp_dir / "timeline.json").write_text("{}", encoding="utf-8")
            # 缺 review_script.md / 横竖屏 srt
            (out_dir / "demo_特写_高光.mp4").write_bytes(b"x")
            (out_dir / "demo_全景_高光.mp4").write_bytes(b"x")
            (out_dir / "demo_混剪_高光.mp4").write_bytes(b"x")
            with self.assertRaises(FileNotFoundError):
                pack_deliver(temp_dir, out_dir, "demo")

    def test_pack_from_video_paths(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            temp_dir = root / "temp" / "demo"
            out_dir = root / "output" / "demo"
            scratch = root / "scratch"
            temp_dir.mkdir(parents=True)
            out_dir.mkdir(parents=True)
            scratch.mkdir()

            (temp_dir / "timeline.json").write_text("{}", encoding="utf-8")
            (temp_dir / "review_script.md").write_text("r", encoding="utf-8")
            (temp_dir / "highlight_竖屏.srt").write_text("1\n", encoding="utf-8")
            (temp_dir / "highlight_横屏.srt").write_text("1\n", encoding="utf-8")
            paths = {
                "closeup": scratch / "c.mp4",
                "wide": scratch / "w.mp4",
                "mix": scratch / "m.mp4",
            }
            for p in paths.values():
                p.write_bytes(b"v")

            packed = pack_deliver(temp_dir, out_dir, "demo", video_paths=paths)
            self.assertTrue((packed / "demo_特写_高光.mp4").is_file())
            self.assertEqual(len(list(packed.iterdir())), 6)


if __name__ == "__main__":
    unittest.main()
