"""STT 缓存与 SRT 单测。"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from lapi.stt import (  # noqa: E402
    load_cache,
    save_cache,
    transcribe_video,
    words_to_srt,
)


class TestSttCache(unittest.TestCase):
    def test_save_and_load(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            cache = Path(td)
            data = {"text": "你好", "words": []}
            save_cache(cache, "abc", data)
            loaded = load_cache(cache, "abc")
            self.assertEqual(loaded["text"], "你好")

    def test_corrupt_cache_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            cache = Path(td)
            path = cache / "bad.json"
            path.write_text("{not-json", encoding="utf-8")
            # md5 filename expected
            (cache / "deadbeef.json").write_text("{broken", encoding="utf-8")
            self.assertIsNone(load_cache(cache, "deadbeef"))

    def test_cache_hit_skips_api(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            video = root / "v.mp4"
            video.write_bytes(b"fake-video-bytes")
            cache = root / "cache"
            temp = root / "temp"
            # pre-seed cache with correct md5 via transcribe path helpers
            from lapi.stt import file_md5

            md5 = file_md5(video)
            save_cache(cache, md5, {"text": "cached", "words": []})

            with patch("lapi.stt.extract_audio") as ex, patch(
                "lapi.stt.call_elevenlabs_stt"
            ) as api:
                result, got_md5, from_cache = transcribe_video(
                    video, cache_dir=cache, temp_dir=temp, api_key="k"
                )
                self.assertTrue(from_cache)
                self.assertEqual(got_md5, md5)
                self.assertEqual(result["text"], "cached")
                ex.assert_not_called()
                api.assert_not_called()

    def test_words_to_srt(self) -> None:
        words = [
            {"text": "今天", "start": 0.0, "end": 0.4},
            {"text": "很好", "start": 0.4, "end": 0.8},
            {"text": "。", "start": 0.8, "end": 0.9},
        ]
        srt = words_to_srt(words, max_chars=10)
        self.assertIn("-->", srt)
        self.assertIn("今天", srt)


if __name__ == "__main__":
    unittest.main()
