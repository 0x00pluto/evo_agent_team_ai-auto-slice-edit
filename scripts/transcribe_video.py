#!/usr/bin/env python3
"""单独转写入口（可复跑、只刷新字幕）。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lapi.stt import transcribe_video, words_to_srt


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="视频语音转写（ElevenLabs + MD5 缓存）")
    p.add_argument("video_path")
    p.add_argument("--theme", default="", help="归档到 temp/<theme>/（工作区，非交付包）")
    p.add_argument("--force", action="store_true")
    args = p.parse_args(argv)

    video = Path(args.video_path)
    cache_dir = ROOT / "cache" / "transcripts"
    temp_dir = ROOT / "temp" / (args.theme or "stt")
    result, md5, from_cache = transcribe_video(
        video, cache_dir=cache_dir, temp_dir=temp_dir, force=args.force
    )
    print(f"md5={md5} cache={'HIT' if from_cache else 'MISS'}")
    print(result.get("text", "")[:200])

    if args.theme:
        work = ROOT / "temp" / args.theme
        work.mkdir(parents=True, exist_ok=True)
        with (work / "transcript.json").open("w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        (work / "transcript.srt").write_text(
            words_to_srt(result.get("words") or []), encoding="utf-8"
        )
        print(f"已归档到工作区: {work}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
