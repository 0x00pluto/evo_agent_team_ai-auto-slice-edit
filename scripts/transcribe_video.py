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
from lapi.theme_dir import allocate_temp_dir, resolve_temp_dir


def _resolve_or_allocate(theme: str) -> Path:
    """已有工作区则复用最新戳；否则新建带戳目录。"""
    try:
        return resolve_temp_dir(ROOT / "temp", theme)
    except FileNotFoundError:
        return allocate_temp_dir(ROOT / "temp", theme)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="视频语音转写（ElevenLabs + MD5 缓存）")
    p.add_argument("video_path")
    p.add_argument(
        "--theme",
        default="",
        help="归档到 temp/<theme>_YYYY_MM_DD_HH_MM/（短名即可；已有则复用最新戳）",
    )
    p.add_argument("--force", action="store_true")
    args = p.parse_args(argv)

    video = Path(args.video_path)
    cache_dir = ROOT / "cache" / "transcripts"
    if args.theme:
        temp_dir = _resolve_or_allocate(args.theme)
    else:
        temp_dir = allocate_temp_dir(ROOT / "temp", "stt")
    result, md5, from_cache = transcribe_video(
        video, cache_dir=cache_dir, temp_dir=temp_dir, force=args.force
    )
    print(f"md5={md5} cache={'HIT' if from_cache else 'MISS'}")
    print(result.get("text", "")[:200])

    if args.theme:
        work = temp_dir
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
