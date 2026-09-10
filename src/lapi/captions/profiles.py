"""字幕屏型配置：竖屏 14 / 横屏 20（可改常量）。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CaptionProfile:
    name: str
    max_chars: int
    filename: str


VERTICAL = CaptionProfile(name="竖屏", max_chars=14, filename="highlight_竖屏.srt")
HORIZONTAL = CaptionProfile(name="横屏", max_chars=20, filename="highlight_横屏.srt")

ALL_PROFILES: tuple[CaptionProfile, ...] = (VERTICAL, HORIZONTAL)
