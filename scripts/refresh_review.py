#!/usr/bin/env python3
"""根据 temp/<theme>/timeline.json + transcript.json 重写 review_script.md（无模型调用）。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lapi.director.review import render_review_script
from lapi.timeline import load_timeline


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="刷新审阅稿")
    p.add_argument("--theme", required=True)
    args = p.parse_args(argv)

    work = ROOT / "temp" / args.theme
    tl_path = work / "timeline.json"
    tr_path = work / "transcript.json"
    if not tl_path.exists():
        print(f"找不到: {tl_path}", file=sys.stderr)
        return 1
    if not tr_path.exists():
        print(f"找不到: {tr_path}", file=sys.stderr)
        return 1

    tl = load_timeline(tl_path)
    tr = json.loads(tr_path.read_text(encoding="utf-8"))
    md = render_review_script(tl, tr.get("words") or [], theme=args.theme)
    path = work / "review_script.md"
    path.write_text(md, encoding="utf-8")
    print(f"→ {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
