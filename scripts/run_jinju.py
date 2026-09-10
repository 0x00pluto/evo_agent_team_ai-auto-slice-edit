#!/usr/bin/env python3
"""金句筛选 CLI：nominate / export（多轴条）/ pack（焊尾进三片 + jinju 备选）。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lapi.jinju.export import export_all
from lapi.jinju.pack import pack_jinju
from lapi.jinju.schema import (
    JinjuCandidate,
    JinjuCandidates,
    candidates_path,
    jinju_work_dir,
    load_candidates,
)
from lapi.jinju.sources import axis_label_cn, resolve_source_axes
from lapi.theme_dir import resolve_temp_dir


def _theme_dirs(theme: str) -> tuple[Path, Path]:
    """output 短名；temp 解析戳目录（或精确名）。"""
    return ROOT / "output" / theme, resolve_temp_dir(ROOT / "temp", theme)

def _load_sources(temp_dir: Path) -> dict:
    path = temp_dir / "sources.json"
    if not path.is_file():
        raise FileNotFoundError(f"缺 sources.json: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def cmd_nominate(args: argparse.Namespace) -> int:
    """写入/覆盖 candidates 草稿（可由 Agent 预填，人再改）。"""
    try:
        _out_dir, temp_dir = _theme_dirs(args.theme)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 1
    work = jinju_work_dir(temp_dir)
    work.mkdir(parents=True, exist_ok=True)
    path = candidates_path(temp_dir)

    if path.is_file() and not args.force:
        print(f"已存在 {path}（加 --force 覆盖）", file=sys.stderr)
        return 1

    if args.from_json:
        raw = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
        from lapi.jinju.schema import validate_candidates

        doc = validate_candidates({**raw, "theme": raw.get("theme") or args.theme})
    else:
        doc = JinjuCandidates(
            theme=args.theme,
            recommended=0,
            notes="请按 src/lapi/jinju/prompts/select.md 填入 2～3 条候选后 export",
            candidates=[
                JinjuCandidate(
                    start=0.0,
                    end=1.0,
                    quote="（占位，请替换）",
                    delivery="punchy",
                    reason="占位",
                    shot="closeup",
                    slug="placeholder",
                )
            ],
            stats={"status": "draft"},
        )

    doc.save(path)
    print(f"nominate → {path}")
    print("下一步: 编辑 candidates.json → run_jinju.py export --theme …")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    try:
        out_dir, temp_dir = _theme_dirs(args.theme)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 1
    path = candidates_path(temp_dir)
    if not path.is_file():
        print(f"缺 {path}；先 nominate 或手写 candidates.json", file=sys.stderr)
        return 1

    doc = load_candidates(path)
    if not doc.theme:
        doc.theme = args.theme

    sources = _load_sources(temp_dir)
    overrides: dict[str, Path] = {}
    if args.closeup:
        overrides["closeup"] = Path(args.closeup)
    if args.wide:
        overrides["wide"] = Path(args.wide)

    axes = resolve_source_axes(sources, overrides=overrides or None)
    print(
        f"export theme={args.theme} candidates={len(doc.candidates)} "
        f"axes={','.join(f'{k}({axis_label_cn(k)})' for k, _ in axes)}"
    )
    result = export_all(
        theme=args.theme,
        sources=sources,
        doc=doc,
        temp_theme_dir=temp_dir,
        axis_overrides=overrides or None,
    )
    for k, v in result.items():
        if k == "axes" and isinstance(v, dict):
            for axis, paths in v.items():
                for p in paths:
                    print(f"  → [{axis_label_cn(axis)}] {p}")
        elif isinstance(v, list):
            continue
        elif v and Path(v).exists():
            print(f"  → {v}")
    print("下一步: run_jinju.py pack --theme …（把推荐收尾焊进三条成片）")
    return 0


def cmd_pack(args: argparse.Namespace) -> int:
    try:
        out_dir, temp_dir = _theme_dirs(args.theme)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 1
    print(f"pack jinju theme={args.theme} temp={temp_dir.name}（焊尾进三片 + jinju 备选）")
    packed = pack_jinju(temp_dir, out_dir)
    print(f"  → {packed}")
    for p in sorted(packed.iterdir()):
        print(f"     {p.name}")
    for name in (
        f"{args.theme}_特写_高光.mp4",
        f"{args.theme}_全景_高光.mp4",
        f"{args.theme}_混剪_高光.mp4",
    ):
        p = out_dir / name
        if p.is_file():
            print(f"  → {p}（已含推荐收尾）")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="金句筛选：多轴备选 + 焊入三条成片末尾（无第四条）"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    nom = sub.add_parser("nominate", help="写入 candidates.json 草稿")
    nom.add_argument("--theme", required=True)
    nom.add_argument("--force", action="store_true")
    nom.add_argument("--from-json", help="从已有 JSON 导入（校验后写入）")
    nom.set_defaults(func=cmd_nominate)

    exp = sub.add_parser("export", help="按 sources 轴数裁切同时间码金句条 + 审阅")
    exp.add_argument("--theme", required=True)
    exp.add_argument("--closeup", help="覆盖 sources.json 特写路径")
    exp.add_argument("--wide", help="覆盖 sources.json 全景路径")
    exp.set_defaults(func=cmd_export)

    pk = sub.add_parser(
        "pack",
        help="jinju/ 备选 + 推荐收尾焊进特写/全景/混剪三片",
    )
    pk.add_argument("--theme", required=True)
    pk.set_defaults(func=cmd_pack)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
