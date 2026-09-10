#!/usr/bin/env python3
"""双机位拉片 CLI：plan（转写+导演，停闸门） / cut（确认后出片） / pack（组装交付包）。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lapi.cutter import render_all
from lapi.deliver import pack_deliver
from lapi.director import direct_auto_result, render_review_script
from lapi.highlight_srt import ensure_highlight_srt
from lapi.jinju.pack import snapshot_narrative_bases
from lapi.stt import transcribe_video, words_to_srt
from lapi.theme_dir import allocate_temp_dir, resolve_temp_dir
from lapi.timeline import load_timeline


def _output_dir(theme: str) -> Path:
    """交付包目录：不打戳。"""
    return ROOT / "output" / theme


def _temp_for_plan(theme: str) -> Path:
    """新建成片工作区：带东八区时间戳。"""
    return allocate_temp_dir(ROOT / "temp", theme)


def _temp_resolve(theme: str) -> Path:
    """解析已有 temp 工作区（精确或短名→最新戳）。"""
    return resolve_temp_dir(ROOT / "temp", theme)

def cmd_plan(args: argparse.Namespace) -> int:
    wide = Path(args.wide)
    closeup = Path(args.closeup)
    if not closeup.exists():
        print(f"特写不存在: {closeup}", file=sys.stderr)
        return 1
    if args.wide and not wide.exists():
        print(f"全景不存在: {wide}", file=sys.stderr)
        return 1

    _out_dir = _output_dir(args.theme)
    temp_dir = _temp_for_plan(args.theme)
    print(f"temp 工作区 → {temp_dir}")
    cache_dir = ROOT / "cache" / "transcripts"

    print("=" * 50)
    print("plan Step 1/2: STT（特写）")
    print("=" * 50)
    result, md5, from_cache = transcribe_video(
        closeup,
        cache_dir=cache_dir,
        temp_dir=temp_dir,
        force=args.force_stt,
    )
    print(f"  md5={md5}  cache={'HIT' if from_cache else 'MISS'}")

    transcript_path = temp_dir / "transcript.json"
    with transcript_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    srt_path = temp_dir / "transcript.srt"
    srt_path.write_text(words_to_srt(result.get("words") or []), encoding="utf-8")
    print(f"  → {transcript_path}")
    print(f"  → {srt_path}")

    # 记录源路径，供 cut 使用
    sources = {
        "theme": args.theme,
        "wide": str(wide.resolve()) if args.wide else "",
        "closeup": str(closeup.resolve()),
        "transcript_md5": md5,
    }
    sources_path = temp_dir / "sources.json"
    with sources_path.open("w", encoding="utf-8") as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)

    print("=" * 50)
    print(f"plan Step 2/2: 自动导演（target={args.target_seconds}s）")
    print("=" * 50)
    result_dir = direct_auto_result(
        result,
        target_seconds=args.target_seconds,
        theme=args.theme,
    )
    timeline = result_dir.timeline
    timeline_path = temp_dir / "timeline.json"
    timeline.save(timeline_path)

    words = result.get("words") or []
    review = render_review_script(timeline, words, theme=args.theme)
    review_path = temp_dir / "review_script.md"
    review_path.write_text(review, encoding="utf-8")

    print(
        f"  内容拍 {result_dir.stats.content_beats} → "
        f"成片段 {len(timeline.segments)}，合计 {timeline.total_duration():.1f}s"
    )
    print(
        f"  语气词切除 {result_dir.stats.filler_cuts} 处 / "
        f"{result_dir.stats.filler_seconds:.1f}s"
    )
    print(f"  → {timeline_path}")
    print(f"  → {review_path}")
    print()
    print("人工闸门：请审阅 temp/<theme>/review_script.md 与 timeline.json。")
    print("确认后执行：")
    print(
        f"  .venv/bin/python scripts/run_dualcam_lapi.py cut "
        f"--theme {args.theme}"
    )

    if args.yes_cut:
        print()
        print("已指定 --yes-cut，继续裁切…")
        return cmd_cut(
            argparse.Namespace(
                theme=args.theme,
                timeline=str(timeline_path),
                wide=args.wide or None,
                closeup=args.closeup,
            )
        )
    return 0


def cmd_cut(args: argparse.Namespace) -> int:
    out_dir = _output_dir(args.theme)
    try:
        temp_dir = _temp_resolve(args.theme)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 1
    print(f"temp 工作区 → {temp_dir}")
    timeline_path = (
        Path(args.timeline) if args.timeline else temp_dir / "timeline.json"
    )
    if not timeline_path.exists():
        print(f"找不到 timeline: {timeline_path}", file=sys.stderr)
        return 1

    timeline = load_timeline(timeline_path)
    if not timeline.theme:
        timeline.theme = args.theme

    sources_path = temp_dir / "sources.json"
    wide = Path(args.wide) if args.wide else None
    closeup = Path(args.closeup) if args.closeup else None
    if sources_path.exists():
        with sources_path.open("r", encoding="utf-8") as f:
            sources = json.load(f)
        if wide is None and sources.get("wide"):
            wide = Path(sources["wide"])
        if closeup is None and sources.get("closeup"):
            closeup = Path(sources["closeup"])

    if wide is None or closeup is None:
        print(
            "cut 需要 --wide/--closeup，或先跑 plan 生成 temp/<theme>/sources.json",
            file=sys.stderr,
        )
        return 1
    if not wide.exists() or not closeup.exists():
        print(f"源视频缺失: wide={wide} closeup={closeup}", file=sys.stderr)
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    print("=" * 50)
    print("cut: ffmpeg 出三片（同时间轴）")
    print("=" * 50)
    paths = render_all(
        wide,
        closeup,
        timeline,
        out_dir,
        temp_dir / "cuts",
        theme=args.theme,
    )
    for label, path in paths.items():
        print(f"  {label}: {path}")

    # 叙事底片快照：供金句 pack 焊尾可重入（避免二次叠尾）
    snap = snapshot_narrative_bases(
        args.theme,
        temp_dir,
        video_paths=paths,
        output_dir=out_dir,
        force=True,
    )
    print(f"  narrative 底片 → {snap}")

    print("=" * 50)
    print("captions: 横竖屏成片轴字幕（草稿；Agent 可纠错别字）")
    print("=" * 50)
    try:
        srt_path = ensure_highlight_srt(temp_dir, force=True)
    except (FileNotFoundError, ValueError, OSError) as e:
        print(f"生成字幕失败: {e}", file=sys.stderr)
        return 1
    print(f"  → {srt_path}")
    print(f"  → {temp_dir / 'highlight_横屏.srt'}")

    print("=" * 50)
    print("pack: 组装干净交付包 → output/<theme>/")
    print("=" * 50)
    try:
        packed = pack_deliver(temp_dir, out_dir, args.theme, video_paths=paths)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 1
    print(f"  → {packed}")
    return 0


def cmd_pack(args: argparse.Namespace) -> int:
    out_dir = _output_dir(args.theme)
    try:
        temp_dir = _temp_resolve(args.theme)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 1
    print("=" * 50)
    print(f"pack: 组装交付包 theme={args.theme} temp={temp_dir.name}")
    print("=" * 50)
    try:
        srt_path = ensure_highlight_srt(temp_dir, force=False)
        print(f"  captions: {srt_path.name} + highlight_横屏.srt")
        packed = pack_deliver(temp_dir, out_dir, args.theme)
    except (FileNotFoundError, ValueError, OSError) as e:
        print(str(e), file=sys.stderr)
        return 1
    print(f"  → {packed}")
    for p in sorted(packed.iterdir()):
        print(f"    {p.name}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="双机位自动拉片（plan 闸门 / cut 出片 / pack 交付）"
    )
    sub = p.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan", help="转写+导演，写出审阅稿后停止（默认不合成）")
    plan.add_argument("--wide", required=True, help="全景视频路径")
    plan.add_argument("--closeup", required=True, help="特写视频路径（用于 STT）")
    plan.add_argument(
        "--theme",
        required=True,
        help="主题短名；plan 会建 temp/<短名>_YYYY_MM_DD_HH_MM/，output 仍用短名",
    )
    plan.add_argument("--target-seconds", type=float, default=120.0)
    plan.add_argument("--force-stt", action="store_true", help="忽略缓存强制重转写")
    plan.add_argument(
        "--yes-cut",
        action="store_true",
        help="无人值守：导演后立即 cut（日常勿用）",
    )
    plan.set_defaults(func=cmd_plan)

    cut = sub.add_parser("cut", help="审阅确认后，按 timeline 切三片并组装交付包")
    cut.add_argument("--theme", required=True)
    cut.add_argument(
        "--timeline",
        default="",
        help="默认 temp/<theme>/timeline.json",
    )
    cut.add_argument("--wide", default="", help="可覆盖 sources.json")
    cut.add_argument("--closeup", default="", help="可覆盖 sources.json")
    cut.set_defaults(func=cmd_cut)

    pack = sub.add_parser(
        "pack",
        help="仅组装 output/<theme>/ 交付包（不重裁；需 temp 文稿 + 已有三片）",
    )
    pack.add_argument("--theme", required=True)
    pack.set_defaults(func=cmd_pack)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    # 空字符串转 None
    if getattr(args, "wide", None) == "":
        args.wide = None
    if getattr(args, "closeup", None) == "":
        args.closeup = None
    if getattr(args, "timeline", None) == "":
        args.timeline = None
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
