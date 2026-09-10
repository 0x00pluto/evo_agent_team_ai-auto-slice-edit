"""时间轴 JSON 契约：全景/特写共用 segments；混剪另读 shot。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

Shot = Literal["wide", "closeup"]


@dataclass
class Segment:
    start: float
    end: float
    shot: Shot
    reason: str = ""

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    def to_dict(self) -> dict[str, Any]:
        return {
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "shot": self.shot,
            "reason": self.reason,
        }


@dataclass
class Timeline:
    target_seconds: float
    audio_source: Literal["closeup", "wide"]
    segments: list[Segment]
    theme: str = ""
    stats: dict[str, Any] = field(default_factory=dict)

    def total_duration(self) -> float:
        return sum(s.duration for s in self.segments)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "theme": self.theme,
            "target_seconds": self.target_seconds,
            "audio_source": self.audio_source,
            "total_duration": round(self.total_duration(), 3),
            "segments": [s.to_dict() for s in self.segments],
        }
        if self.stats:
            data["stats"] = self.stats
        return data

    def save(self, path: Path | str) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)


def _as_float(value: Any, name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as e:
        raise ValueError(f"segment.{name} 必须是数字") from e


def parse_segment(raw: dict[str, Any]) -> Segment:
    if not isinstance(raw, dict):
        raise ValueError("segment 必须是对象")
    start = _as_float(raw.get("start"), "start")
    end = _as_float(raw.get("end"), "end")
    if end <= start:
        raise ValueError(f"segment end ({end}) 必须大于 start ({start})")
    shot = raw.get("shot", "closeup")
    if shot not in ("wide", "closeup"):
        raise ValueError(f"shot 必须是 wide|closeup，收到: {shot!r}")
    reason = str(raw.get("reason") or "")
    return Segment(start=start, end=end, shot=shot, reason=reason)


def load_timeline(path: Path | str) -> Timeline:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return validate_timeline(data)


def validate_timeline(data: Any) -> Timeline:
    if not isinstance(data, dict):
        raise ValueError("timeline 根节点必须是对象")
    if "segments" not in data or not isinstance(data["segments"], list):
        raise ValueError("timeline.segments 必须是数组")
    if not data["segments"]:
        raise ValueError("timeline.segments 不能为空")

    segments = [parse_segment(s) for s in data["segments"]]
    for i in range(1, len(segments)):
        if segments[i].start < segments[i - 1].end - 1e-6:
            raise ValueError(
                f"segments[{i}] 与上一段重叠或乱序: "
                f"{segments[i - 1].end} → {segments[i].start}"
            )

    audio_source = data.get("audio_source", "closeup")
    if audio_source not in ("closeup", "wide"):
        raise ValueError("audio_source 必须是 closeup|wide")

    target = float(data.get("target_seconds", 120))
    theme = str(data.get("theme") or "")
    stats = data.get("stats") if isinstance(data.get("stats"), dict) else {}
    return Timeline(
        target_seconds=target,
        audio_source=audio_source,
        segments=segments,
        theme=theme,
        stats=stats,
    )
