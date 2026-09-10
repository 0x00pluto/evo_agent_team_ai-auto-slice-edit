"""cleanup_temp_media：可删目标集与 apply 后残留。"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "cleanup_temp_media.py"


def _load_cleanup():
    spec = importlib.util.spec_from_file_location("cleanup_temp_media", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cleanup_temp_media"] = mod
    spec.loader.exec_module(mod)
    return mod


cleanup = _load_cleanup()


class CleanupTempMediaTest(unittest.TestCase):
    def _touch(self, path: Path, data: bytes = b"x") -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def test_targets_and_apply_keeps_work_files(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            theme = temp / "DemoTheme"
            # keep
            self._touch(theme / "sources.json", b"{}")
            self._touch(theme / "sources.md", b"# s")
            self._touch(theme / "transcript.json", b"{}")
            self._touch(theme / "timeline.json", b"{}")
            self._touch(theme / "review_script.md", b"# r")
            self._touch(theme / "highlight_竖屏.srt", b"1\n")
            self._touch(theme / "aligned" / "wide_concat.txt", b"file 'a'\n")
            self._touch(theme / "cut_cs03.py", b"#\n")
            self._touch(theme / "jinju" / "axes.txt", b"0\n")
            self._touch(theme / "jinju" / "candidates.json", b"[]")
            self._touch(theme / "jinju" / "review.md", b"# j")
            # delete
            self._touch(theme / "aligned" / "aligned_wide.mp4", b"M" * 100)
            self._touch(theme / "source_concat.mp4", b"C" * 50)
            self._touch(theme / "cuts" / "mix" / "a.mp4", b"c" * 40)
            self._touch(theme / "narrative" / "n.mp4", b"n" * 30)
            self._touch(theme / "jinju" / "00_foo_特写.mp4", b"j" * 20)
            self._touch(theme / "jinju" / "_bake" / "b.mp4", b"b" * 10)
            self._touch(theme / "jinju" / "_preview" / "p.mp4", b"p" * 10)
            self._touch(theme / "audio.abc.mp3", b"a" * 8)
            # orphan part
            part = temp / "DemoTheme_part1"
            self._touch(part / "transcript.json", b"{}")

            targets = cleanup.iter_cleanup_targets(
                None, temp_root=temp, orphan_parts=True
            )
            names = {str(t.relative_to(temp)) for t in targets}
            self.assertIn("DemoTheme/aligned/aligned_wide.mp4", names)
            self.assertIn("DemoTheme/source_concat.mp4", names)
            self.assertIn("DemoTheme/cuts", names)
            self.assertIn("DemoTheme/narrative", names)
            self.assertIn("DemoTheme/jinju/00_foo_特写.mp4", names)
            self.assertIn("DemoTheme/jinju/_bake", names)
            self.assertIn("DemoTheme/jinju/_preview", names)
            self.assertIn("DemoTheme/audio.abc.mp3", names)
            self.assertIn("DemoTheme_part1", names)
            # must not target keep files
            for keep in (
                "DemoTheme/sources.json",
                "DemoTheme/transcript.json",
                "DemoTheme/timeline.json",
                "DemoTheme/aligned/wide_concat.txt",
                "DemoTheme/jinju/axes.txt",
                "DemoTheme/cut_cs03.py",
            ):
                self.assertNotIn(keep, names)

            cleanup.apply_cleanup(targets)

            self.assertTrue((theme / "sources.json").is_file())
            self.assertTrue((theme / "transcript.json").is_file())
            self.assertTrue((theme / "timeline.json").is_file())
            self.assertTrue((theme / "aligned" / "wide_concat.txt").is_file())
            self.assertTrue((theme / "jinju" / "axes.txt").is_file())
            self.assertTrue((theme / "cut_cs03.py").is_file())
            self.assertFalse((theme / "aligned" / "aligned_wide.mp4").exists())
            self.assertFalse((theme / "cuts").exists())
            self.assertFalse((theme / "narrative").exists())
            self.assertFalse((theme / "jinju" / "00_foo_特写.mp4").exists())
            self.assertFalse(part.exists())

    def test_orphan_parts_off(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            theme = temp / "Foo"
            self._touch(theme / "transcript.json", b"{}")
            part = temp / "Foo_part2"
            self._touch(part / "transcript.json", b"{}")
            targets = cleanup.iter_cleanup_targets(
                "Foo", temp_root=temp, orphan_parts=False
            )
            self.assertFalse(any(t.name == "Foo_part2" for t in targets))


if __name__ == "__main__":
    unittest.main()
