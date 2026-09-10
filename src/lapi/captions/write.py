"""写出横竖屏两套高光成片轴字幕。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lapi.captions.format import format_quote_as_cues, pack_words_to_cues
from lapi.captions.profiles import ALL_PROFILES, CaptionProfile
from lapi.timeline import Timeline, load_timeline


def _load_words(transcript_path: Path) -> list[dict[str, Any]]:
    with transcript_path.open("r", encoding="utf-8") as f:
        transcript = json.load(f)
    words = transcript.get("words") if isinstance(transcript, dict) else None
    if not isinstance(words, list):
        raise ValueError(f"transcript 无 words 列表: {transcript_path}")
    return words


def build_caption_srt_for_profile(
    timeline: Timeline,
    words: list[dict[str, Any]],
    profile: CaptionProfile,
    *,
    jinju_quote: str | None = None,
    jinju_start: float | None = None,
    jinju_end: float | None = None,
) -> str:
    # 延迟导入：避免与 highlight_srt 循环依赖
    from lapi.highlight_srt import map_words_to_highlight_timeline

    mapped = map_words_to_highlight_timeline(words, timeline)
    cues = pack_words_to_cues(mapped, profile.max_chars)
    if jinju_quote and jinju_start is not None and jinju_end is not None:
        cues.extend(
            format_quote_as_cues(
                jinju_quote, jinju_start, jinju_end, profile.max_chars
            )
        )
    from lapi.captions.format import cues_to_srt

    return cues_to_srt(cues)


def write_caption_set(
    temp_dir: Path | str,
    *,
    timeline_path: Path | str | None = None,
    transcript_path: Path | str | None = None,
    output_dir: Path | str | None = None,
    jinju_quote: str | None = None,
    jinju_start: float | None = None,
    jinju_end: float | None = None,
    remove_legacy_highlight: bool = True,
) -> dict[str, Path]:
    """写 highlight_竖屏.srt / highlight_横屏.srt 到 temp，可选同步到 output。"""
    temp_dir = Path(temp_dir)
    tl_path = Path(timeline_path) if timeline_path else temp_dir / "timeline.json"
    tr_path = Path(transcript_path) if transcript_path else temp_dir / "transcript.json"
    if not tl_path.is_file():
        raise FileNotFoundError(f"缺少 timeline: {tl_path}")
    if not tr_path.is_file():
        raise FileNotFoundError(f"缺少 transcript: {tr_path}")

    timeline = load_timeline(tl_path)
    words = _load_words(tr_path)
    written: dict[str, Path] = {}

    for profile in ALL_PROFILES:
        srt = build_caption_srt_for_profile(
            timeline,
            words,
            profile,
            jinju_quote=jinju_quote,
            jinju_start=jinju_start,
            jinju_end=jinju_end,
        )
        dest = temp_dir / profile.filename
        dest.write_text(srt, encoding="utf-8")
        written[profile.name] = dest
        if output_dir is not None:
            out = Path(output_dir)
            out.mkdir(parents=True, exist_ok=True)
            out_dest = out / profile.filename
            out_dest.write_text(srt, encoding="utf-8")
            written[f"output:{profile.name}"] = out_dest

    if remove_legacy_highlight:
        for base in (temp_dir, Path(output_dir) if output_dir else None):
            if base is None:
                continue
            legacy = Path(base) / "highlight.srt"
            if legacy.is_file():
                legacy.unlink()

    return written


def ensure_caption_set(
    temp_dir: Path | str,
    *,
    force: bool = False,
    output_dir: Path | str | None = None,
) -> dict[str, Path]:
    """若竖屏/横屏均已存在且非 force，则跳过生成。"""
    temp_dir = Path(temp_dir)
    paths = [temp_dir / p.filename for p in ALL_PROFILES]
    if not force and all(p.is_file() for p in paths):
        result = {p.name: temp_dir / p.filename for p in ALL_PROFILES}
        if output_dir is not None:
            out = Path(output_dir)
            out.mkdir(parents=True, exist_ok=True)
            for p in ALL_PROFILES:
                src = temp_dir / p.filename
                dest = out / p.filename
                dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
                result[f"output:{p.name}"] = dest
            legacy = out / "highlight.srt"
            if legacy.is_file():
                legacy.unlink()
        return result
    return write_caption_set(temp_dir, output_dir=output_dir)
