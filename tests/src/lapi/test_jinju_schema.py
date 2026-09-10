"""金句 candidates schema 校验。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from lapi.jinju.schema import validate_candidates  # noqa: E402


class TestJinjuSchema(unittest.TestCase):
    def test_ok(self) -> None:
        doc = validate_candidates(
            {
                "theme": "demo",
                "recommended": 0,
                "candidates": [
                    {
                        "start": 10.0,
                        "end": 18.5,
                        "quote": "这是个组织问题。",
                        "delivery": "punchy",
                        "reason": "铿锵",
                    }
                ],
            }
        )
        self.assertEqual(doc.theme, "demo")
        self.assertEqual(doc.candidates[0].delivery, "punchy")

    def test_bad_delivery(self) -> None:
        with self.assertRaises(ValueError):
            validate_candidates(
                {
                    "theme": "demo",
                    "candidates": [
                        {
                            "start": 1,
                            "end": 2,
                            "quote": "x",
                            "delivery": "soft",
                        }
                    ],
                }
            )

    def test_recommended_oob(self) -> None:
        with self.assertRaises(ValueError):
            validate_candidates(
                {
                    "theme": "demo",
                    "recommended": 2,
                    "candidates": [
                        {
                            "start": 1,
                            "end": 2,
                            "quote": "x",
                            "delivery": "falling",
                        }
                    ],
                }
            )


if __name__ == "__main__":
    unittest.main()
