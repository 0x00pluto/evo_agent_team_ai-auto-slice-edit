"""金句多轴 sources 解析。"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from lapi.jinju.export import candidate_filename  # noqa: E402
from lapi.jinju.schema import JinjuCandidate  # noqa: E402
from lapi.jinju.sources import resolve_source_axes  # noqa: E402


class TestJinjuSources(unittest.TestCase):
    def test_dual_axes_from_sources(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            closeup = root / "c.mp4"
            wide = root / "w.mp4"
            closeup.write_bytes(b"c")
            wide.write_bytes(b"w")
            axes = resolve_source_axes(
                {"theme": "t", "closeup": str(closeup), "wide": str(wide)}
            )
            self.assertEqual([k for k, _ in axes], ["closeup", "wide"])

    def test_three_axes_nested(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            paths = {}
            for name in ("closeup", "wide", "side"):
                p = root / f"{name}.mp4"
                p.write_bytes(b"x")
                paths[name] = str(p)
            axes = resolve_source_axes({"theme": "t", "axes": paths})
            self.assertEqual([k for k, _ in axes], ["closeup", "wide", "side"])

    def test_filename_has_axis_suffix(self) -> None:
        c = JinjuCandidate(
            start=1,
            end=2,
            quote="金句",
            delivery="punchy",
            slug="金句",
        )
        self.assertEqual(candidate_filename(0, c, "closeup"), "00_金句_特写.mp4")
        self.assertEqual(candidate_filename(0, c, "wide"), "00_金句_全景.mp4")


if __name__ == "__main__":
    unittest.main()
