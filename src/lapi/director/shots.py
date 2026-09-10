"""内容拍内镜头语言：保留区间 → 多段 shot（仅在停顿切镜）。"""

from __future__ import annotations

from typing import Any

from lapi.timeline import Segment, Shot


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x) for x in value]
    return [str(value)]


def _text_has(text: str, keywords: list[str]) -> bool:
    low = text.lower()
    return any(k.lower() in low for k in keywords if k)


def _pause_points(
    words: list[dict[str, Any]],
    k0: float,
    k1: float,
    pause_gap: float,
) -> list[float]:
    """保留片内可切点：词间隙 ≥ pause_gap 时取后一词 start。"""
    seq = [
        w
        for w in words
        if float(w["start"]) >= k0 - 1e-3 and float(w["end"]) <= k1 + 1e-3
    ]
    if len(seq) < 2:
        return []
    pts: list[float] = []
    for prev, cur in zip(seq, seq[1:]):
        gap = float(cur["start"]) - float(prev["end"])
        if gap >= pause_gap:
            t = float(cur["start"])
            if k0 + 0.4 < t < k1 - 0.4:
                pts.append(t)
    return pts


def _nearest_pause(
    pauses: list[float], target: float, lo: float, hi: float
) -> float | None:
    cands = [p for p in pauses if lo <= p <= hi]
    if not cands:
        return None
    return min(cands, key=lambda p: abs(p - target))


def plan_shots(
    keep_ranges: list[tuple[float, float]],
    text: str,
    *,
    reason: str,
    shot_cfg: dict[str, Any],
    beat_index: int = 0,
    words: list[dict[str, Any]] | None = None,
    pause_gap: float = 0.6,
) -> list[Segment]:
    """
    对语气词快剪后的保留区间挂机位。
    定场/换气只在停顿点切开；无停顿则整段一种 shot。
    """
    if not keep_ranges:
        return []

    min_shot = float(shot_cfg.get("min_shot_seconds", 2.5))
    establish = float(shot_cfg.get("establish_wide_seconds", 2.5))
    max_close = float(shot_cfg.get("max_closeup_run_seconds", 8))
    wide_kw = _as_list(shot_cfg.get("wide_keywords"))
    theme_kw = _as_list(shot_cfg.get("theme_force_closeup_keywords"))
    punchline = bool(int(shot_cfg.get("punchline_closeup", 1)))
    words = words or []

    force_close = punchline and _text_has(text, theme_kw)

    raw: list[Segment] = []
    for ri, (k0, k1) in enumerate(keep_ranges):
        dur = k1 - k0
        if dur <= 0:
            continue
        base_reason = reason
        pauses = _pause_points(words, k0, k1, pause_gap)

        # 礼仪主导 → 整段全景
        if _text_has(text, wide_kw) and not force_close and dur < max_close + establish:
            raw.append(
                Segment(k0, k1, "wide", f"{base_reason} | 镜头:礼仪/定场全景")
            )
            continue

        # 短片或无可用停顿 → 整段一镜（默认特写；礼仪已在上面处理）
        if dur < min_shot * 2 or not pauses:
            shot: Shot = "closeup"
            label = "特写干货"
            if force_close:
                label = "主题特写"
            raw.append(Segment(k0, k1, shot, f"{base_reason} | 镜头:{label}"))
            continue

        cursor = k0
        # 开头定场：在 establish 附近找停顿
        if ri == 0 and dur >= establish + min_shot:
            cut = _nearest_pause(
                pauses, k0 + establish, k0 + min_shot, k1 - min_shot
            )
            if cut is not None and cut - k0 >= min_shot * 0.85:
                raw.append(
                    Segment(k0, cut, "wide", f"{base_reason} | 镜头:定场")
                )
                cursor = cut

        # 特写为主，在 max_close 附近的停顿处换气
        while cursor < k1 - 1e-6:
            remain = k1 - cursor
            if remain <= min_shot * 1.1:
                if raw and abs(raw[-1].end - cursor) < 1e-3:
                    raw[-1] = Segment(
                        raw[-1].start, k1, raw[-1].shot, raw[-1].reason
                    )
                else:
                    raw.append(
                        Segment(cursor, k1, "closeup", f"{base_reason} | 镜头:收束")
                    )
                break

            target = cursor + max_close
            if target >= k1 - min_shot:
                raw.append(
                    Segment(cursor, k1, "closeup", f"{base_reason} | 镜头:特写干货")
                )
                break

            cut = _nearest_pause(
                pauses, target, cursor + min_shot, k1 - min_shot
            )
            if cut is None:
                # 后面没有停顿：整段特写收完
                raw.append(
                    Segment(cursor, k1, "closeup", f"{base_reason} | 镜头:特写干货")
                )
                break

            raw.append(
                Segment(cursor, cut, "closeup", f"{base_reason} | 镜头:特写干货")
            )
            cursor = cut

            # 换气全景：再找一个短停顿窗
            breath_end = _nearest_pause(
                pauses,
                cursor + establish,
                cursor + min_shot * 0.85,
                min(k1 - min_shot, cursor + establish + 1.5),
            )
            if breath_end is not None and k1 - breath_end >= min_shot * 0.85:
                raw.append(
                    Segment(
                        cursor, breath_end, "wide", f"{base_reason} | 镜头:换气"
                    )
                )
                cursor = breath_end
            # 否则继续下一段特写（cursor 已在停顿点）

    return _merge_short_shots(raw, min_shot)


def _merge_short_shots(segments: list[Segment], min_shot: float) -> list[Segment]:
    if not segments:
        return []
    out: list[Segment] = [segments[0]]
    for seg in segments[1:]:
        last = out[-1]
        gap = seg.start - last.end
        can_bridge = gap <= 0.35
        if gap > 1e-3 and not can_bridge:
            out.append(seg)
            continue
        if can_bridge and (seg.duration < min_shot or last.duration < min_shot):
            shot = (
                "closeup"
                if "closeup" in (last.shot, seg.shot)
                else last.shot
            )
            out[-1] = Segment(
                last.start,
                seg.end,
                shot,
                last.reason if last.duration >= seg.duration else seg.reason,
            )
            continue
        if gap <= 1e-3 and (
            seg.duration < min_shot
            or last.duration < min_shot
            or last.shot == seg.shot
        ):
            if last.shot == seg.shot or seg.duration < min_shot or last.duration < min_shot:
                shot = (
                    "closeup"
                    if "closeup" in (last.shot, seg.shot)
                    else last.shot
                )
                out[-1] = Segment(
                    last.start,
                    seg.end,
                    shot,
                    last.reason if last.duration >= seg.duration else seg.reason,
                )
            else:
                out.append(seg)
        else:
            out.append(seg)

    i = 0
    while i < len(out):
        if out[i].duration + 1e-6 >= min_shot * 0.85 or len(out) == 1:
            i += 1
            continue
        if i + 1 < len(out) and out[i + 1].start - out[i].end <= 0.35:
            nxt = out[i + 1]
            out[i] = Segment(
                out[i].start,
                nxt.end,
                "closeup" if "closeup" in (out[i].shot, nxt.shot) else out[i].shot,
                nxt.reason,
            )
            del out[i + 1]
            continue
        if i > 0 and out[i].start - out[i - 1].end <= 0.35:
            prev = out[i - 1]
            out[i - 1] = Segment(
                prev.start,
                out[i].end,
                "closeup" if "closeup" in (prev.shot, out[i].shot) else prev.shot,
                prev.reason,
            )
            del out[i]
            continue
        i += 1
    # 强制合并仍低于 min_shot 的镜（跨小缝）
    changed = True
    while changed and len(out) > 1:
        changed = False
        for i in range(len(out)):
            if out[i].duration + 1e-6 >= min_shot * 0.85:
                continue
            if i + 1 < len(out) and out[i + 1].start - out[i].end <= 0.5:
                nxt = out[i + 1]
                out[i] = Segment(
                    out[i].start,
                    nxt.end,
                    "closeup" if "closeup" in (out[i].shot, nxt.shot) else out[i].shot,
                    nxt.reason,
                )
                del out[i + 1]
                changed = True
                break
            if i > 0 and out[i].start - out[i - 1].end <= 0.5:
                prev = out[i - 1]
                out[i - 1] = Segment(
                    prev.start,
                    out[i].end,
                    "closeup" if "closeup" in (prev.shot, out[i].shot) else prev.shot,
                    prev.reason,
                )
                del out[i]
                changed = True
                break
    return out
