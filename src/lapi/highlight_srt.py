"""高光成片轴词映射；字幕组装改走 captions 横竖屏模块。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lapi.captions.write import ensure_caption_set, write_caption_set
from lapi.timeline import Timeline, load_timeline


def _normalize_words(raw: list[Any]) -> list[dict[str, Any]]:
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
            start = float(w["start"])
            end = float(w["end"])
        except (KeyError, TypeError, ValueError):
            continue
        if end < start:
            continue
        out.append({"text": text, "start": start, "end": end})
    return out


def map_words_to_highlight_timeline(
    words: list[dict[str, Any]],
    timeline: Timeline,
) -> list[dict[str, Any]]:
    """把源片词级时间码映射到高光成片轴（从 0 起连续）。

    词落入 segment 的判定：词中点在 [seg.start, seg.end]（右闭合），
    与裁切听感一致；映射公式：t' = t - seg.start + cursor。
    """
    normalized = _normalize_words(words)
    mapped: list[dict[str, Any]] = []
    cursor = 0.0
    for seg in timeline.segments:
        for w in normalized:
            mid = (w["start"] + w["end"]) / 2.0
            if mid < seg.start or mid > seg.end:
                continue
            mapped.append(
                {
                    "text": w["text"],
                    "start": w["start"] - seg.start + cursor,
                    "end": w["end"] - seg.start + cursor,
                }
            )
        cursor += seg.duration
    return mapped


def write_highlight_srt(
    temp_dir: Path | str,
    *,
    timeline_path: Path | str | None = None,
    transcript_path: Path | str | None = None,
    out_path: Path | str | None = None,
    max_chars: int = 14,
) -> Path:
    """兼容入口：写出横竖屏两套；返回竖屏路径。

    out_path / max_chars 保留签名但不生成 highlight.srt。
    """
    del out_path, max_chars  # 不再使用单文件/单上限
    written = write_caption_set(
        temp_dir,
        timeline_path=timeline_path,
        transcript_path=transcript_path,
    )
    return written["竖屏"]


def ensure_highlight_srt(temp_dir: Path | str, *, force: bool = False) -> Path:
    """兼容入口：确保横竖屏两套存在；返回竖屏路径。"""
    written = ensure_caption_set(temp_dir, force=force)
    return written["竖屏"]


def timeline_to_highlight_srt(
    timeline: Timeline,
    words: list[dict[str, Any]],
    *,
    max_chars: int = 14,
) -> str:
    """测试/兼容：按竖屏默认上限生成单份 SRT 文本。"""
    from lapi.captions.format import words_to_caption_srt

    mapped = map_words_to_highlight_timeline(words, timeline)
    return words_to_caption_srt(mapped, max_chars=max_chars)
