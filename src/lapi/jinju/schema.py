"""金句候选 JSON 契约：与主 timeline 隔离。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

Delivery = Literal["falling", "punchy"]
Shot = Literal["wide", "closeup"]


@dataclass
class JinjuCandidate:
    start: float
    end: float
    quote: str
    delivery: Delivery
    reason: str = ""
    shot: Shot = "closeup"
    slug: str = ""

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "shot": self.shot,
            "quote": self.quote,
            "delivery": self.delivery,
            "reason": self.reason,
        }
        if self.slug:
            d["slug"] = self.slug
        return d


@dataclass
class JinjuCandidates:
    theme: str
    candidates: list[JinjuCandidate]
    recommended: int = 0
    notes: str = ""
    stats: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "theme": self.theme,
            "recommended": self.recommended,
            "candidates": [c.to_dict() for c in self.candidates],
        }
        if self.notes:
            data["notes"] = self.notes
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
        raise ValueError(f"candidate.{name} 必须是数字") from e


def parse_candidate(raw: dict[str, Any], index: int) -> JinjuCandidate:
    if not isinstance(raw, dict):
        raise ValueError(f"candidates[{index}] 必须是对象")
    start = _as_float(raw.get("start"), "start")
    end = _as_float(raw.get("end"), "end")
    if end <= start:
        raise ValueError(f"candidates[{index}] end ({end}) 必须大于 start ({start})")
    delivery = raw.get("delivery")
    if delivery not in ("falling", "punchy"):
        raise ValueError(
            f"candidates[{index}].delivery 必须是 falling|punchy，收到: {delivery!r}"
        )
    shot = raw.get("shot", "closeup")
    if shot not in ("wide", "closeup"):
        raise ValueError(f"candidates[{index}].shot 必须是 wide|closeup")
    quote = str(raw.get("quote") or "").strip()
    if not quote:
        raise ValueError(f"candidates[{index}].quote 不能为空")
    reason = str(raw.get("reason") or "")
    slug = str(raw.get("slug") or "")
    return JinjuCandidate(
        start=start,
        end=end,
        quote=quote,
        delivery=delivery,  # type: ignore[arg-type]
        reason=reason,
        shot=shot,  # type: ignore[arg-type]
        slug=slug,
    )


def validate_candidates(data: Any) -> JinjuCandidates:
    if not isinstance(data, dict):
        raise ValueError("jinju candidates 根节点必须是对象")
    theme = str(data.get("theme") or "")
    raw_list = data.get("candidates")
    if not isinstance(raw_list, list) or not raw_list:
        raise ValueError("candidates 必须是非空数组")
    if len(raw_list) > 5:
        raise ValueError("candidates 最多 5 条（建议 2～3）")
    candidates = [parse_candidate(c, i) for i, c in enumerate(raw_list)]
    recommended = int(data.get("recommended", 0))
    if recommended < 0 or recommended >= len(candidates):
        raise ValueError(
            f"recommended={recommended} 超出 candidates 下标 0..{len(candidates) - 1}"
        )
    notes = str(data.get("notes") or "")
    stats = data.get("stats") if isinstance(data.get("stats"), dict) else {}
    return JinjuCandidates(
        theme=theme,
        candidates=candidates,
        recommended=recommended,
        notes=notes,
        stats=stats,
    )


def load_candidates(path: Path | str) -> JinjuCandidates:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return validate_candidates(data)


def jinju_work_dir(temp_theme_dir: Path) -> Path:
    """temp/<theme>/jinju/"""
    return Path(temp_theme_dir) / "jinju"


def candidates_path(temp_theme_dir: Path) -> Path:
    return jinju_work_dir(temp_theme_dir) / "candidates.json"
