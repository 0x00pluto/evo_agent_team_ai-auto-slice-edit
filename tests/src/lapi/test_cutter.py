"""裁切命令构造与 timeline 契约；plan/cut 闸门。"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from lapi.cutter import (  # noqa: E402
    cut_segment_cmd,
    render_all,
    write_concat_list,
)
from lapi.timeline import Timeline, Segment, load_timeline, validate_timeline  # noqa: E402


class TestTimeline(unittest.TestCase):
    def test_validate_ok(self) -> None:
        tl = validate_timeline(
            {
                "target_seconds": 120,
                "audio_source": "closeup",
                "segments": [
                    {"start": 1, "end": 10, "shot": "wide", "reason": "a"},
                    {"start": 20, "end": 30, "shot": "closeup", "reason": "b"},
                ],
            }
        )
        self.assertEqual(len(tl.segments), 2)

    def test_overlap_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_timeline(
                {
                    "segments": [
                        {"start": 1, "end": 10, "shot": "closeup"},
                        {"start": 9, "end": 15, "shot": "closeup"},
                    ]
                }
            )


class TestCutter(unittest.TestCase):
    def test_cut_cmd_same_audio(self) -> None:
        cmd = cut_segment_cmd(Path("/a.mp4"), 1.5, 3.5, Path("/o.mp4"))
        self.assertIn("ffmpeg", cmd)
        self.assertIn("-ss", cmd)
        self.assertIn("libx264", cmd)

    def test_cut_cmd_remap_audio(self) -> None:
        cmd = cut_segment_cmd(
            Path("/wide.mp4"),
            2.0,
            5.0,
            Path("/o.mp4"),
            audio_from=Path("/close.mp4"),
        )
        self.assertIn("-map", cmd)
        self.assertEqual(cmd.count("-i"), 2)

    def test_same_timeline_both_cameras(self) -> None:
        tl = Timeline(
            target_seconds=30,
            audio_source="closeup",
            segments=[
                Segment(1.0, 5.0, "wide", "w"),
                Segment(10.0, 18.0, "closeup", "c"),
            ],
            theme="t",
        )
        calls: list[list[str]] = []

        def fake_run(cmd, check=True, capture_output=True):
            calls.append(list(cmd))
            return MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            wide = root / "w.mp4"
            close = root / "c.mp4"
            wide.write_bytes(b"x")
            close.write_bytes(b"y")
            out = root / "out"
            temp = root / "temp"
            render_all(wide, close, tl, out, temp, theme="t", run=fake_run)

        # 两路单机位各 2 段 + 混剪 2 段 = 至少 6 次 cut + 3 次 concat
        cut_calls = [c for c in calls if "libx264" in c]
        self.assertEqual(len(cut_calls), 6)
        # 全景与特写裁切时间应对齐
        wide_ss = [c[c.index("-ss") + 1] for c in cut_calls if str(wide) in c]
        close_ss = [
            c[c.index("-ss") + 1]
            for c in cut_calls
            if str(close) in c and c.count("-i") == 1
        ]
        self.assertEqual(wide_ss[:2], ["1.000", "10.000"])
        self.assertEqual(close_ss[:2], ["1.000", "10.000"])

    def test_concat_list(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a = root / "a.mp4"
            a.write_bytes(b"1")
            list_path = root / "list.txt"
            write_concat_list([a], list_path)
            text = list_path.read_text(encoding="utf-8")
            self.assertIn("file '", text)


class TestCliGate(unittest.TestCase):
    def test_plan_does_not_cut_without_flag(self) -> None:
        import run_dualcam_lapi as cli

        with tempfile.TemporaryDirectory() as td:
            # redirect ROOT via patching module constants is hard; instead
            # spy on render_all / cmd_cut
            fake_result = {
                "text": "词0词1",
                "words": [
                    {"text": "词0", "start": 10.0, "end": 10.4},
                    {"text": "词1", "start": 10.5, "end": 18.0},
                ],
            }
            # pad more words for min segment
            words = []
            t = 20.0
            for i in range(40):
                words.append({"text": f"a{i}", "start": t, "end": t + 0.4})
                t += 0.5
            words.append({"text": "核心", "start": t, "end": t + 0.5})
            fake_result["words"] = [
                {"text": "欢迎", "start": 12.0, "end": 12.5},
                *words,
            ]
            # add pause then another chunk
            t2 = t + 2
            for i in range(40):
                fake_result["words"].append(
                    {"text": f"b{i}", "start": t2, "end": t2 + 0.4}
                )
                t2 += 0.5

            with patch.object(cli, "ROOT", Path(td)), patch.object(
                cli, "transcribe_video", return_value=(fake_result, "m", True)
            ), patch.object(cli, "render_all") as render, patch.object(
                cli, "cmd_cut"
            ) as cut:
                # need real video paths existing
                wide = Path(td) / "w.mp4"
                close = Path(td) / "c.mp4"
                wide.write_bytes(b"w")
                close.write_bytes(b"c")
                rc = cli.main(
                    [
                        "plan",
                        "--wide",
                        str(wide),
                        "--closeup",
                        str(close),
                        "--theme",
                        "demo",
                        "--target-seconds",
                        "30",
                    ]
                )
                self.assertEqual(rc, 0)
                render.assert_not_called()
                cut.assert_not_called()
                work = Path(td) / "temp" / "demo"
                self.assertTrue((work / "timeline.json").exists())
                self.assertTrue((work / "review_script.md").exists())
                self.assertTrue((work / "transcript.json").exists())
                self.assertTrue((work / "sources.json").exists())
                out = Path(td) / "output" / "demo"
                self.assertFalse(out.exists() or any(out.glob("*") if out.exists() else []))


if __name__ == "__main__":
    unittest.main()
