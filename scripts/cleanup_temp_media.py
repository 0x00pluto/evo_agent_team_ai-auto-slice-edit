#!/usr/bin/env python3
"""清理 temp 下可重建的大媒体；保留 STT cache、片源说明与选句工作文件。

默认 dry-run。加 --apply 才删除。

工作流：docs/workflows/cleanup-temp-media.md

永不删除：
  cache/、transcript*.json、sources.md、sources.json、timeline.json、
  review_script.md、highlight_*.srt、*_concat.txt、concat_list.txt、
  cut_*.py、jinju 文稿（axes/candidates/review/transcript）、以及任意非媒体工作文稿。

可删（交付后）：
  aligned/*.mp4、source_concat.mp4、cuts/、narrative/、
  jinju/_bake/、jinju/_preview/、jinju/*.mp4、audio.<md5>.mp3、
  temp/<theme>_partN/（父主题已有合并 transcript.json 时，默认开）
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMP = ROOT / "temp"

KEEP_NAMES = {
    "sources.md",
    "sources.json",
    "timeline.json",
    "review_script.md",
    "transcript.json",
    "transcript.srt",
    "cut_narrative.py",
    "concat_list.txt",
    "axes.txt",
    "candidates.json",
}

PART_DIR_RE = re.compile(r"^(.+)_part(\d+)$")


def _is_protected(path: Path) -> bool:
    name = path.name
    if name in KEEP_NAMES:
        return True
    if name.startswith("highlight_") and name.endswith(".srt"):
        return True
    if name.endswith("_concat.txt"):
        return True
    if name == "concat_list.txt":
        return True
    if name.startswith("cut_") and name.endswith(".py"):
        return True
    return False


def iter_orphan_part_dirs(temp_root: Path) -> list[Path]:
    """父主题已有 transcript.json 时，返回可删的 *_partN 目录。"""
    out: list[Path] = []
    if not temp_root.is_dir():
        return out
    for p in sorted(temp_root.iterdir()):
        if not p.is_dir() or p.name.startswith("."):
            continue
        m = PART_DIR_RE.match(p.name)
        if not m:
            continue
        parent = temp_root / m.group(1)
        if (parent / "transcript.json").is_file():
            out.append(p)
    return out


def iter_cleanup_targets(
    theme: str | None,
    *,
    temp_root: Path | None = None,
    orphan_parts: bool = True,
) -> list[Path]:
    temp = temp_root if temp_root is not None else TEMP
    roots: list[Path]
    if theme:
        roots = [temp / theme]
    else:
        roots = [
            p
            for p in temp.iterdir()
            if p.is_dir() and not p.name.startswith(".") and not PART_DIR_RE.match(p.name)
        ]

    targets: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        aligned = root / "aligned"
        if aligned.is_dir():
            for mp4 in aligned.glob("*.mp4"):
                targets.append(mp4)
        concat = root / "source_concat.mp4"
        if concat.is_file():
            targets.append(concat)
        for sub in ("cuts", "narrative"):
            d = root / sub
            if d.is_dir():
                targets.append(d)
        jinju = root / "jinju"
        if jinju.is_dir():
            for sub in ("_bake", "_preview"):
                d = jinju / sub
                if d.is_dir():
                    targets.append(d)
            for mp4 in jinju.glob("*.mp4"):
                targets.append(mp4)
        for audio in root.glob("audio.*.mp3"):
            targets.append(audio)

    if orphan_parts:
        if theme:
            m = PART_DIR_RE.match(theme)
            if m:
                # 用户显式指定 part 目录名时：仅当父主题有合并稿才收
                parent = temp / m.group(1)
                part_dir = temp / theme
                if part_dir.is_dir() and (parent / "transcript.json").is_file():
                    targets.append(part_dir)
            else:
                parent = temp / theme
                if (parent / "transcript.json").is_file():
                    for p in iter_orphan_part_dirs(temp):
                        if p.name.startswith(theme + "_part"):
                            targets.append(p)
        else:
            targets.extend(iter_orphan_part_dirs(temp))

    # stable unique
    seen: set[Path] = set()
    out: list[Path] = []
    for t in targets:
        try:
            rp = t.resolve()
        except OSError:
            rp = t
        if rp in seen:
            continue
        if _is_protected(t):
            continue
        seen.add(rp)
        out.append(t)
    return out


def sizeof(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            total += p.stat().st_size
    return total


def fmt(n: int) -> str:
    x = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if x < 1024.0 or unit == "TB":
            if unit == "B":
                return f"{int(x)}B"
            return f"{x:.1f}{unit}"
        x /= 1024.0
    return f"{x:.1f}TB"


def apply_cleanup(targets: list[Path]) -> None:
    for t in targets:
        if t.is_dir():
            shutil.rmtree(t)
        elif t.is_file():
            t.unlink()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="清理 temp 可重建大媒体（默认 dry-run）")
    p.add_argument("--apply", action="store_true", help="真正删除；默认只打印")
    p.add_argument(
        "--theme",
        default="",
        help="只清理 temp/<theme>/（须精确目录名，含时间戳时写全名；不做短名解析）",
    )
    p.add_argument(
        "--orphan-parts",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="父主题有合并 transcript 时删除 *_partN/（默认开）",
    )
    args = p.parse_args(argv)

    if not TEMP.is_dir():
        print(f"无 temp 目录: {TEMP}", file=sys.stderr)
        return 1

    targets = iter_cleanup_targets(
        args.theme or None,
        orphan_parts=bool(args.orphan_parts),
    )
    if not targets:
        print("无可清理目标")
        return 0

    total = 0
    print(f"mode={'APPLY' if args.apply else 'DRY-RUN'} root={TEMP}")
    for t in targets:
        sz = sizeof(t)
        total += sz
        rel = t.relative_to(ROOT) if t.is_relative_to(ROOT) else t
        print(f"  {fmt(sz):>10}  {rel}")
        if args.apply:
            if t.is_dir():
                shutil.rmtree(t)
            elif t.is_file():
                t.unlink()
    print(f"合计约 {fmt(total)}（{'已删除' if args.apply else '未删除'}）")
    print(
        "保留：cache/transcripts、sources.md/json、transcript、timeline、"
        "review、highlight_*.srt、*_concat.txt、jinju 文稿等"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
