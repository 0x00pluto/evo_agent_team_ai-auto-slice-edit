"""规则自动导演：紧选内容拍 → 语气词快剪 → 镜头语言展开。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lapi.director.fillers import cut_fillers
from lapi.director.prompts_loader import (
    clear_prompt_cache,
    load_filler_config,
    load_selection_config,
    load_shot_config,
)
from lapi.director.shots import plan_shots
from lapi.timeline import Segment, Timeline


@dataclass
class _Candidate:
    start: float
    end: float
    text: str
    score: float

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass
class DirectStats:
    filler_cuts: int = 0
    filler_seconds: float = 0.0
    content_beats: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "filler_cuts": self.filler_cuts,
            "filler_seconds": round(self.filler_seconds, 3),
            "content_beats": self.content_beats,
        }


@dataclass
class DirectResult:
    timeline: Timeline
    stats: DirectStats = field(default_factory=DirectStats)


def _words(transcript: dict[str, Any]) -> list[dict[str, Any]]:
    raw = transcript.get("words") or []
    out: list[dict[str, Any]] = []
    for w in raw:
        if not isinstance(w, dict):
            continue
        text = str(w.get("text") or "")
        if not text.strip():
            continue
        if w.get("type") == "spacing":
            continue
        try:
            out.append(
                {
                    "text": text,
                    "start": float(w["start"]),
                    "end": float(w["end"]),
                }
            )
        except (KeyError, TypeError, ValueError):
            continue
    return out


def split_by_pause(
    words: list[dict[str, Any]], pause_gap: float
) -> list[tuple[float, float, str]]:
    if not words:
        return []
    chunks: list[tuple[float, float, str]] = []
    start = words[0]["start"]
    end = words[0]["end"]
    buf = [words[0]["text"]]
    for prev, cur in zip(words, words[1:]):
        gap = cur["start"] - prev["end"]
        if gap >= pause_gap:
            chunks.append((start, end, "".join(buf)))
            start = cur["start"]
            buf = [cur["text"]]
        else:
            buf.append(cur["text"])
        end = cur["end"]
    chunks.append((start, end, "".join(buf)))
    return chunks


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x) for x in value]
    return [str(value)]


def _matched_keywords(text: str, keywords: list[str]) -> list[str]:
    low = text.lower()
    hits: list[str] = []
    for kw in keywords:
        k = kw.strip()
        if not k:
            continue
        if k.lower() in low:
            hits.append(k)
    return hits


def _score_chunk(
    start: float,
    end: float,
    text: str,
    cfg: dict[str, Any],
) -> float:
    dur = end - start
    if dur <= 0:
        return -1e9
    sweet_min = float(cfg.get("sweet_min_seconds", 6))
    sweet_max = float(cfg.get("sweet_max_seconds", 14))
    skip = float(cfg.get("skip_leading_seconds", 8))
    min_seg = float(cfg.get("min_segment_seconds", 5))
    max_seg = float(cfg.get("max_segment_seconds", 16))

    if dur < min_seg * 0.5 or dur > max_seg * 1.5:
        return -1e6

    if sweet_min <= dur <= sweet_max:
        length_score = 1.0
    elif dur < sweet_min:
        length_score = dur / sweet_min
    else:
        length_score = max(0.0, 1.0 - (dur - sweet_max) / sweet_max)

    density = len(text.strip()) / max(dur, 0.1)
    density_score = min(1.5, density / 6.0)

    lead_penalty = 0.85 if start < skip else 0.0

    bonus = 0.0
    for token in ("所以", "因此", "关键", "核心", "第一", "第二", "总结", "%", "亿", "万"):
        if token in text:
            bonus += 0.08

    theme_hits = _matched_keywords(text, _as_list(cfg.get("theme_keywords")))
    theme_bonus = float(cfg.get("theme_keyword_bonus", 3.5)) * len(theme_hits)
    secondary_hits = _matched_keywords(text, _as_list(cfg.get("secondary_keywords")))
    secondary_bonus = float(cfg.get("secondary_keyword_bonus", 0.6)) * len(
        secondary_hits
    )
    demote_hits = _matched_keywords(text, _as_list(cfg.get("demote_keywords")))
    demote_penalty = float(cfg.get("demote_keyword_penalty", 0.9)) * len(demote_hits)

    return (
        length_score * 2.0
        + density_score
        + bonus
        + theme_bonus
        + secondary_bonus
        - demote_penalty
        - lead_penalty
    )


def _merge_near(
    cands: list[_Candidate], merge_gap: float, max_seg: float
) -> list[_Candidate]:
    if not cands:
        return []
    ordered = sorted(cands, key=lambda c: c.start)
    merged: list[_Candidate] = [ordered[0]]
    for c in ordered[1:]:
        last = merged[-1]
        if c.start - last.end <= merge_gap and (c.end - last.start) <= max_seg:
            merged[-1] = _Candidate(
                last.start,
                c.end,
                last.text + c.text,
                max(last.score, c.score),
            )
        else:
            merged.append(c)
    return merged


def _pick_greedy(
    cands: list[_Candidate], target: float, tolerance: float
) -> list[_Candidate]:
    picked: list[_Candidate] = []
    used_ranges: list[tuple[float, float]] = []
    total = 0.0

    def overlaps(a: float, b: float) -> bool:
        return any(a < e and b > s for s, e in used_ranges)

    for c in sorted(cands, key=lambda x: x.score, reverse=True):
        if c.score < 0 or overlaps(c.start, c.end):
            continue
        if total + c.duration > target + tolerance:
            if total >= target - tolerance:
                break
            if total + c.duration > target + tolerance * 2:
                continue
        picked.append(c)
        used_ranges.append((c.start, c.end))
        total += c.duration
        if total >= target - tolerance:
            break
    return sorted(picked, key=lambda c: c.start)


def _snap_to_word_edge(
    words: list[dict[str, Any]], t: float, *, toward: str
) -> float:
    if not words:
        return t
    if toward == "start":
        # 不早于 t 的最近词 start；若无则用 ≤t 的最晚 end
        after = [w["start"] for w in words if w["start"] >= t - 1e-3]
        if after:
            return min(after)
        before = [w["end"] for w in words if w["end"] <= t + 1e-3]
        return max(before) if before else t
    before = [w["end"] for w in words if w["end"] <= t + 1e-3]
    if before:
        return max(before)
    after = [w["start"] for w in words if w["start"] >= t - 1e-3]
    return min(after) if after else t


def trim_to_theme_core(
    words: list[dict[str, Any]],
    start: float,
    end: float,
    text: str,
    cfg: dict[str, Any],
) -> tuple[float, float, str]:
    """以主题词为锚收紧区间；无主题则略收两端。不做小句补全（见 complete_clause）。"""
    themes = _as_list(cfg.get("theme_keywords"))
    hits = _matched_keywords(text, themes)
    pre = float(cfg.get("theme_core_pre_seconds", 4))
    post = float(cfg.get("theme_core_post_seconds", 10))
    min_seg = float(cfg.get("min_segment_seconds", 5))
    max_seg = float(cfg.get("max_segment_seconds", 18))

    in_range = [w for w in words if w["end"] >= start and w["start"] <= end]
    if not in_range:
        return start, end, text

    if hits:
        anchor = None
        for w in in_range:
            low = w["text"].lower()
            if any(h.lower() in low or low in h.lower() for h in hits):
                anchor = w["start"]
                break
        if anchor is None:
            buf = ""
            for w in in_range:
                buf += w["text"]
                if any(h.lower() in buf.lower() for h in hits):
                    anchor = w["start"]
                    break
        if anchor is not None:
            ns = max(start, anchor - pre)
            ne = min(end, anchor + post)
            if ne - ns < min_seg:
                ne = min(end, ns + min_seg)
            if ne - ns > max_seg:
                ne = ns + max_seg
            ns = _snap_to_word_edge(in_range, ns, toward="start")
            ne = _snap_to_word_edge(in_range, ne, toward="end")
            if ne <= ns:
                return start, end, text
            new_text = "".join(
                w["text"]
                for w in in_range
                if w["start"] >= ns - 1e-3 and w["end"] <= ne + 1e-3
            )
            return ns, ne, new_text or text

    if end - start > max_seg:
        ns = end - max_seg
        ns = _snap_to_word_edge(in_range, ns, toward="start")
        new_text = "".join(
            w["text"]
            for w in in_range
            if w["start"] >= ns - 1e-3 and w["end"] <= end + 1e-3
        )
        return ns, end, new_text or text
    return start, end, text


_CLAUSE_END = ("。", "！", "？", "；", ".", "!", "?", ";")


def _excerpt(words: list[dict[str, Any]], start: float, end: float) -> str:
    return "".join(
        w["text"]
        for w in words
        if w["start"] >= start - 1e-3 and w["end"] <= end + 1e-3
    )


def _is_clause_end_word(w: dict[str, Any]) -> bool:
    t = str(w.get("text") or "")
    return any(p in t for p in _CLAUSE_END)


def complete_clause(
    words: list[dict[str, Any]],
    start: float,
    end: float,
    cfg: dict[str, Any],
) -> tuple[float, float, str]:
    """
    把头收到上一停顿之后、把尾扩到下一停顿/句末。
    宁可略超 max_segment，也不半截收刀。
    """
    pause = float(cfg.get("pause_gap_seconds", 0.6))
    ext_end = float(cfg.get("clause_extend_end_seconds", 6))
    ext_pre = float(cfg.get("clause_extend_pre_seconds", 3))

    if not words:
        return start, end, ""

    before_end = [w for w in words if w["end"] <= end + 1e-3]
    after = [w for w in words if w["start"] >= end - 1e-3]

    already_ok = False
    if before_end and _is_clause_end_word(before_end[-1]):
        already_ok = True
    if after and before_end and after[0]["start"] - before_end[-1]["end"] >= pause:
        already_ok = True

    new_end = end
    if not already_ok and after:
        limit = end + ext_end
        prev = before_end[-1] if before_end else after[0]
        for w in after:
            if w["start"] > limit + 1e-3:
                new_end = prev["end"]
                break
            gap = w["start"] - prev["end"]
            if gap >= pause:
                new_end = prev["end"]
                break
            new_end = w["end"]
            if _is_clause_end_word(w):
                break
            prev = w

    # 头：从 start 所在词起，向前找到停顿后的词首
    new_start = start
    limit_pre = start - ext_pre
    # 定位 start 落在/之后的第一个词
    start_idx = 0
    for i, w in enumerate(words):
        if w["end"] >= start - 1e-3:
            start_idx = i
            break
    j = start_idx
    while j > 0 and words[j]["start"] >= limit_pre - 1e-3:
        gap = words[j]["start"] - words[j - 1]["end"]
        if gap >= pause or _is_clause_end_word(words[j - 1]):
            new_start = words[j]["start"]
            break
        j -= 1
    else:
        if words[j]["start"] >= limit_pre - 1e-3:
            new_start = words[j]["start"]

    if new_end <= new_start:
        new_start, new_end = start, end

    return new_start, new_end, _excerpt(words, new_start, new_end)


def _reason_for(c: _Candidate, cfg: dict[str, Any]) -> str:
    dens = len(c.text.strip()) / max(c.duration, 0.1)
    theme_hits = _matched_keywords(c.text, _as_list(cfg.get("theme_keywords")))
    if theme_hits:
        return (
            f"峰会主题[{'/'.join(theme_hits)}] "
            f"score={c.score:.2f} density={dens:.1f}字/秒"
        )
    secondary = _matched_keywords(c.text, _as_list(cfg.get("secondary_keywords")))
    if secondary:
        return (
            f"相关[{'/'.join(secondary)}] "
            f"score={c.score:.2f} density={dens:.1f}字/秒"
        )
    return f"自动选段 score={c.score:.2f} density={dens:.1f}字/秒"


def direct_auto(
    transcript: dict[str, Any],
    *,
    target_seconds: float = 120.0,
    theme: str = "",
    selection_cfg: dict[str, Any] | None = None,
    shot_cfg: dict[str, Any] | None = None,
    filler_cfg: dict[str, Any] | None = None,
) -> Timeline:
    """兼容旧接口：只返回 Timeline。"""
    return direct_auto_result(
        transcript,
        target_seconds=target_seconds,
        theme=theme,
        selection_cfg=selection_cfg,
        shot_cfg=shot_cfg,
        filler_cfg=filler_cfg,
    ).timeline


def direct_auto_result(
    transcript: dict[str, Any],
    *,
    target_seconds: float = 120.0,
    theme: str = "",
    selection_cfg: dict[str, Any] | None = None,
    shot_cfg: dict[str, Any] | None = None,
    filler_cfg: dict[str, Any] | None = None,
) -> DirectResult:
    if selection_cfg is None or shot_cfg is None or filler_cfg is None:
        clear_prompt_cache()
    cfg = selection_cfg if selection_cfg is not None else load_selection_config()
    scfg = shot_cfg if shot_cfg is not None else load_shot_config()
    fcfg = filler_cfg if filler_cfg is not None else load_filler_config()

    words = _words(transcript)
    if not words:
        raise ValueError("转写中没有可用词级时间戳")

    pause = float(cfg.get("pause_gap_seconds", 0.6))
    min_seg = float(cfg.get("min_segment_seconds", 5))
    max_seg = float(cfg.get("max_segment_seconds", 16))
    merge_gap = float(cfg.get("merge_gap_seconds", 0.6))
    tolerance = float(cfg.get("target_tolerance_seconds", 8))

    chunks = split_by_pause(words, pause)
    cands: list[_Candidate] = []
    for start, end, text in chunks:
        dur = end - start
        if dur < min_seg * 0.5:
            continue
        if dur > max_seg:
            t = start
            while t < end - min_seg * 0.5:
                te = min(t + max_seg, end)
                sub = _excerpt(words, t, te)
                score = _score_chunk(t, te, sub, cfg)
                cands.append(_Candidate(t, te, sub, score))
                t += max_seg * 0.7
        else:
            score = _score_chunk(start, end, text, cfg)
            cands.append(_Candidate(start, end, text, score))

    cands = _merge_near(cands, merge_gap, max_seg)

    # 主题核修剪 → 小句补全 → 再打分
    trimmed: list[_Candidate] = []
    for c in cands:
        ns, ne, nt = trim_to_theme_core(words, c.start, c.end, c.text, cfg)
        ns, ne, nt = complete_clause(words, ns, ne, cfg)
        if ne - ns < min_seg * 0.5:
            continue
        score = _score_chunk(ns, ne, nt, cfg)
        trimmed.append(_Candidate(ns, ne, nt, score))
    cands = trimmed or cands

    # 补全后可能重叠：按开始排序去重叠（保留高分）
    cands = sorted(cands, key=lambda x: x.score, reverse=True)
    resolved: list[_Candidate] = []
    used: list[tuple[float, float]] = []
    for c in cands:
        if any(c.start < e and c.end > s for s, e in used):
            continue
        resolved.append(c)
        used.append((c.start, c.end))
    cands = sorted(resolved, key=lambda x: x.start) or trimmed

    picked = _pick_greedy(cands, target_seconds, tolerance)
    if not picked:
        if not cands:
            raise ValueError("无法从转写中切出候选高光段")
        picked = [max(cands, key=lambda c: c.score)]

    stats = DirectStats(content_beats=len(picked))
    segments: list[Segment] = []
    for i, c in enumerate(picked):
        reason = _reason_for(c, cfg)
        keeps, n_cuts, cut_sec = cut_fillers(words, c.start, c.end, fcfg)
        stats.filler_cuts += n_cuts
        stats.filler_seconds += cut_sec
        segs = plan_shots(
            keeps,
            c.text,
            reason=reason,
            shot_cfg=scfg,
            beat_index=i,
            words=words,
            pause_gap=pause,
        )
        segments.extend(segs)

    # 按时间排序；允许缝隙（语气词挖空）
    segments.sort(key=lambda s: (s.start, s.end))

    timeline = Timeline(
        target_seconds=float(target_seconds),
        audio_source="closeup",
        segments=segments,
        theme=theme,
        stats=stats.to_dict(),
    )
    return DirectResult(timeline=timeline, stats=stats)
