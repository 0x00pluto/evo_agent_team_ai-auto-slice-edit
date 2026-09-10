"""把 timeline 渲染成给人审阅的拉片脚本 Markdown。"""

from __future__ import annotations

from typing import Any

from lapi.timeline import Timeline


def _tc(seconds: float) -> str:
    ms = int(round(max(0.0, seconds) * 1000))
    h, rem = divmod(ms, 3600_000)
    m, rem = divmod(rem, 60_000)
    s, milli = divmod(rem, 1000)
    if h:
        return f"{h:d}:{m:02d}:{s:02d}.{milli:03d}"
    return f"{m:02d}:{s:02d}.{milli:03d}"


def excerpt_for_range(
    words: list[dict[str, Any]], start: float, end: float, limit: int = 120
) -> str:
    parts: list[str] = []
    for w in words:
        try:
            ws = float(w["start"])
            we = float(w["end"])
        except (KeyError, TypeError, ValueError):
            continue
        if we < start or ws > end:
            continue
        text = str(w.get("text") or "")
        if text:
            parts.append(text)
    text = "".join(parts).strip()
    if len(text) > limit:
        return text[: limit - 1] + "…"
    return text


def render_review_script(
    timeline: Timeline,
    words: list[dict[str, Any]],
    *,
    theme: str,
    source_note: str = "特写音轨转写",
) -> str:
    stats = timeline.stats or {}
    lines = [
        f"# 拉片审阅稿 · {theme}",
        "",
        f"- 目标时长: **{timeline.target_seconds:.0f}s**",
        f"- 实际选段总长: **{timeline.total_duration():.1f}s**",
        f"- 片段数: **{len(timeline.segments)}**（含镜头切换；内容拍 {stats.get('content_beats', '—')}）",
        f"- 语气词切除: **{stats.get('filler_cuts', 0)} 处 / 约 {stats.get('filler_seconds', 0):.1f}s**",
        f"- 共用时间轴音源: `{timeline.audio_source}`（{source_note}）",
        f"- 混剪画面: 按每段 `shot`；音频固定 `{timeline.audio_source}`",
        "",
        "> 审阅通过后执行 `cut`。可直接改 `timeline.json`，或改 `src/lapi/director/prompts/` 后重跑 `plan`。",
        "",
        "| # | 时间码 | 时长 | shot | reason | 口播摘录 |",
        "|---|--------|------|------|--------|----------|",
    ]
    for i, seg in enumerate(timeline.segments, start=1):
        excerpt = excerpt_for_range(words, seg.start, seg.end).replace("|", "\\|")
        reason = (seg.reason or "").replace("|", "\\|")
        lines.append(
            f"| {i} | {_tc(seg.start)} → {_tc(seg.end)} | {seg.duration:.1f}s | "
            f"`{seg.shot}` | {reason} | {excerpt} |"
        )
    lines.append("")
    lines.append("## 分段正文")
    lines.append("")
    for i, seg in enumerate(timeline.segments, start=1):
        excerpt = excerpt_for_range(words, seg.start, seg.end, limit=400)
        lines.append(f"### {i}. {_tc(seg.start)} → {_tc(seg.end)}（`{seg.shot}`）")
        lines.append("")
        lines.append(f"- reason: {seg.reason or '—'}")
        lines.append(f"- 摘录: {excerpt or '（无词）'}")
        lines.append("")
    return "\n".join(lines)
