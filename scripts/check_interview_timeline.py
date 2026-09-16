#!/usr/bin/env python3
"""访谈粗剪 timeline 交稿验收（无 LLM）。

检查：合计时长 vs target_seconds、禁止单段跨 T0、`t < T0` 仅当时机位、
段起/止词半截启发式。供父 agent / subagent 交稿前跑；退出码非 0 = 未过门。
"""

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

# 段起点若落在这些「接上句」标记上，多半是半截起刀（勿把「是/有/在」等合法句首算进去）
_BAD_START_EXACT = frozenset({"，", ",", "。", "、", "的", "了", "着", "过"})
_BAD_START_PREFIXES = (
    "然后",
    "从而",
    "哪些",
    "他成为",
    "成为一个",
    "然后去",
    "然后从",
    "而去",
)


def _load_words(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: list[dict] = []
    for w in data.get("words") or []:
        if w.get("type") == "spacing":
            continue
        text = str(w.get("text") or "").strip()
        if not text:
            continue
        try:
            ws, we = float(w["start"]), float(w["end"])
        except (KeyError, TypeError, ValueError):
            continue
        out.append({"start": ws, "end": we, "text": text})
    return out


_PUNCT = frozenset({"，", ",", "。", "、", "；", ";", "：", ":", "！", "!", "？", "?", "…", "—", "-"})


def _is_punct(text: str) -> bool:
    t = text.strip()
    return (not t) or t in _PUNCT or all(c in _PUNCT for c in t)


def _content_span_at_start(words: list[dict], t: float) -> tuple[dict | None, str]:
    """段起点：第一个非标点词；若单字「然」且下一词为「后」，拼成「然后」供启发式。"""
    first: dict | None = None
    idx = -1
    for i, w in enumerate(words):
        if w["end"] < t - 1e-3:
            continue
        if _is_punct(w["text"]):
            continue
        first = w
        idx = i
        break
    if first is None:
        return None, ""
    text = first["text"]
    if text == "然" and idx + 1 < len(words):
        nxt = words[idx + 1]
        if nxt["text"] == "后" and nxt["start"] <= first["end"] + 0.5:
            text = "然后"
    return first, text


def _content_word_at_end(words: list[dict], t: float) -> dict | None:
    """段终点：取 t 处或之前的最后一个非标点词。"""
    last: dict | None = None
    for w in words:
        if w["start"] > t + 1e-3:
            break
        if _is_punct(w["text"]):
            continue
        last = w
    return last


def _looks_half_start(text: str) -> bool:
    t = text.strip()
    if not t or _is_punct(t):
        return True
    if t in _BAD_START_EXACT:
        return True
    for p in _BAD_START_PREFIXES:
        if t.startswith(p):
            return True
    return False


def _looks_half_end(text: str) -> bool:
    t = text.strip()
    if not t:
        return True
    # 收在明显未完的介词/连词；「的」作句尾定语太常见，不算失败
    if t in {"和", "与", "或", "把", "被", "让", "从"}:
        return True
    return False


def check_timeline(
    work: Path,
    *,
    tolerance: float,
    skip_half: bool,
) -> list[str]:
    errors: list[str] = []
    tl_path = work / "timeline.json"
    tr_path = work / "transcript.json"
    if not tl_path.is_file():
        return [f"缺少 {tl_path}"]
    if not tr_path.is_file():
        return [f"缺少 {tr_path}"]

    tl = json.loads(tl_path.read_text(encoding="utf-8"))
    segs = tl.get("segments") or []
    if not segs:
        return ["segments 为空"]

    target = float(tl.get("target_seconds") or 0)
    stats = tl.get("stats") if isinstance(tl.get("stats"), dict) else {}
    t0 = stats.get("T0")
    if t0 is None:
        src_path = work / "sources.json"
        if src_path.is_file():
            src = json.loads(src_path.read_text(encoding="utf-8"))
            t0 = src.get("T0")
    if t0 is None:
        errors.append("缺少 T0（timeline.stats.T0 或 sources.json.T0）")
        t0_f = None
    else:
        t0_f = float(t0)

    total = 0.0
    for i, raw in enumerate(segs):
        try:
            start = float(raw["start"])
            end = float(raw["end"])
        except (KeyError, TypeError, ValueError):
            errors.append(f"segment[{i}] start/end 无效")
            continue
        shot = str(raw.get("shot") or "")
        if end <= start:
            errors.append(f"segment[{i}] end<=start ({start}–{end})")
            continue
        dur = end - start
        total += dur

        if t0_f is not None:
            if start < t0_f <= end:
                errors.append(
                    f"segment[{i}] 跨 T0={t0_f}: {start:.3f}–{end:.3f}"
                )
            if start < t0_f and shot != "wide":
                errors.append(
                    f"segment[{i}] P1(t<T0) 必须 wide，实际 shot={shot!r} "
                    f"@ {start:.3f}"
                )

    if target > 0:
        delta = abs(total - target)
        if delta > tolerance + 1e-6:
            errors.append(
                f"时长 {total:.1f}s 偏离 target={target:.1f}s "
                f"（|Δ|={delta:.1f}s > tolerance={tolerance:.1f}s）"
            )

    if not skip_half:
        words = _load_words(tr_path)
        for i, raw in enumerate(segs):
            try:
                start = float(raw["start"])
                end = float(raw["end"])
            except (KeyError, TypeError, ValueError):
                continue
            _w0, start_text = _content_span_at_start(words, start)
            w1 = _content_word_at_end(words, end)
            if start_text and _looks_half_start(start_text):
                errors.append(
                    f"segment[{i}] 疑似半截起刀 @ {start:.3f} "
                    f"词={start_text!r}"
                )
            if w1 and _looks_half_end(w1["text"]):
                errors.append(
                    f"segment[{i}] 疑似半截收刀 @ {end:.3f} "
                    f"词={w1['text']!r}"
                )

    return errors


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="访谈 timeline 交稿验收：时长 / 禁跨 T0 / t<T0 仅当时机位 / 半截启发式"
    )
    p.add_argument("--theme", required=True, help="temp 工作区短名或带戳全名")
    p.add_argument(
        "--tolerance",
        type=float,
        default=3.0,
        help="合计时长相对 target_seconds 容差秒数（默认 3）",
    )
    p.add_argument(
        "--skip-half",
        action="store_true",
        help="跳过半截句启发式（只查时长/T0/镜头）",
    )
    args = p.parse_args(argv)

    try:
        work = resolve_temp_dir(ROOT / "temp", args.theme)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 1

    errors = check_timeline(
        work, tolerance=args.tolerance, skip_half=args.skip_half
    )
    tl = json.loads((work / "timeline.json").read_text(encoding="utf-8"))
    segs = tl.get("segments") or []
    total = sum(
        float(s["end"]) - float(s["start"])
        for s in segs
        if "start" in s and "end" in s
    )
    target = float(tl.get("target_seconds") or 0)
    print(f"theme={work.name}")
    print(f"segments={len(segs)} total={total:.1f}s target={target:.1f}s "
          f"tolerance={args.tolerance:.1f}s")
    if errors:
        print(f"FAIL ({len(errors)})")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
