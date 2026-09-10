#!/usr/bin/env python3
"""按时间窗导出带 index 的词表，供 Agent 语义快剪提示词粘贴。不调用任何模型 API。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lapi.theme_dir import resolve_temp_dir


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="导出时间窗内词级时间码（无 LLM）")
    p.add_argument("--theme", required=True, help="temp 工作区短名或带戳全名")
    p.add_argument("--start", type=float, required=True)
    p.add_argument("--end", type=float, required=True)
    p.add_argument(
        "--pad-after",
        type=float,
        default=8.0,
        help="尾后多导出多少秒，便于扩尾判断（默认 8）",
    )
    p.add_argument(
        "--pad-before",
        type=float,
        default=2.0,
        help="头前多导出多少秒（默认 2）",
    )
    args = p.parse_args(argv)

    try:
        work = resolve_temp_dir(ROOT / "temp", args.theme)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 1
    path = work / "transcript.json"
    if not path.exists():
        print(f"找不到: {path}", file=sys.stderr)
        return 1

    data = json.loads(path.read_text(encoding="utf-8"))
    words = data.get("words") or []
    lo = args.start - args.pad_before
    hi = args.end + args.pad_after

    print(
        f"# theme={work.name} window=[{lo:.3f},{hi:.3f}] "
        f"core=[{args.start:.3f},{args.end:.3f}]"
    )
    print("# index\tstart\tend\ttext")
    idx = 0
    for w in words:
        if w.get("type") == "spacing":
            continue
        text = str(w.get("text") or "")
        if not text.strip():
            continue
        try:
            ws, we = float(w["start"]), float(w["end"])
        except (KeyError, TypeError, ValueError):
            continue
        if we < lo or ws > hi:
            continue
        mark = ""
        if ws >= args.start - 1e-3 and we <= args.end + 1e-3:
            mark = " *"
        print(f"{idx}\t{ws:.3f}\t{we:.3f}\t{text}{mark}")
        idx += 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
