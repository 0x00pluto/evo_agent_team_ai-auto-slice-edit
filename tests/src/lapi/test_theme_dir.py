"""temp 工作区时间戳目录：allocate / resolve。"""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from lapi.theme_dir import (  # noqa: E402
    CST,
    allocate_temp_dir,
    cst_stamp,
    parse_stamped_name,
    resolve_temp_dir,
)


class TestCstStamp(unittest.TestCase):
    def test_format_asia_shanghai(self) -> None:
        when = datetime(2026, 9, 10, 17, 50, tzinfo=CST)
        self.assertEqual(cst_stamp(when), "2026_09_10_17_50")

    def test_naive_treated_as_cst(self) -> None:
        when = datetime(2026, 9, 10, 9, 5)
        self.assertEqual(cst_stamp(when), "2026_09_10_09_05")

    def test_utc_converts_to_cst(self) -> None:
        when = datetime(2026, 9, 10, 9, 50, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(cst_stamp(when), "2026_09_10_17_50")


class TestParseStampedName(unittest.TestCase):
    def test_basic(self) -> None:
        self.assertEqual(
            parse_stamped_name("刘探书访谈CS04_2026_09_10_17_50"),
            ("刘探书访谈CS04", "2026_09_10_17_50", 1),
        )

    def test_collision_suffix(self) -> None:
        self.assertEqual(
            parse_stamped_name("foo_2026_09_10_17_50__2"),
            ("foo", "2026_09_10_17_50", 2),
        )

    def test_hub_without_stamp(self) -> None:
        self.assertIsNone(parse_stamped_name("刘探书访谈OPC"))

    def test_prefix_not_false_stamp(self) -> None:
        # 枢纽名含数字但不构成完整戳
        self.assertIsNone(parse_stamped_name("刘探书访谈"))


class TestAllocateTempDir(unittest.TestCase):
    def test_empty_creates_stamped(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            when = datetime(2026, 9, 10, 17, 50, tzinfo=CST)
            path = allocate_temp_dir(root, "Demo", when=when)
            self.assertEqual(path.name, "Demo_2026_09_10_17_50")
            self.assertTrue(path.is_dir())

    def test_same_minute_gets_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            when = datetime(2026, 9, 10, 17, 50, tzinfo=CST)
            a = allocate_temp_dir(root, "Demo", when=when)
            b = allocate_temp_dir(root, "Demo", when=when)
            c = allocate_temp_dir(root, "Demo", when=when)
            self.assertEqual(a.name, "Demo_2026_09_10_17_50")
            self.assertEqual(b.name, "Demo_2026_09_10_17_50__2")
            self.assertEqual(c.name, "Demo_2026_09_10_17_50__3")


class TestResolveTempDir(unittest.TestCase):
    def test_exact_hub(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            hub = root / "刘探书访谈OPC"
            hub.mkdir()
            self.assertEqual(resolve_temp_dir(root, "刘探书访谈OPC"), hub)

    def test_short_name_picks_latest_stamp(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old = root / "刘探书访谈CS04_2026_09_10_17_40"
            new = root / "刘探书访谈CS04_2026_09_10_17_50"
            newer = root / "刘探书访谈CS04_2026_09_10_17_50__2"
            old.mkdir()
            new.mkdir()
            newer.mkdir()
            # 同分钟 __2 视为更新
            self.assertEqual(
                resolve_temp_dir(root, "刘探书访谈CS04"), newer
            )

    def test_exact_stamped_name(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a = root / "Demo_2026_09_10_17_40"
            b = root / "Demo_2026_09_10_17_50"
            a.mkdir()
            b.mkdir()
            self.assertEqual(
                resolve_temp_dir(root, "Demo_2026_09_10_17_40"), a
            )

    def test_hub_not_matched_by_shorter_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "刘探书访谈OPC").mkdir()
            with self.assertRaises(FileNotFoundError):
                resolve_temp_dir(root, "刘探书访谈")

    def test_missing_raises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaises(FileNotFoundError):
                resolve_temp_dir(root, "不存在主题")


if __name__ == "__main__":
    unittest.main()
