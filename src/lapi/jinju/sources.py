"""从 sources.json 解析机位轴：有几路有效视频路径就出几轴。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 非机位字段
_SKIP_KEYS = frozenset(
    {
        "theme",
        "transcript_md5",
        "md5",
        "notes",
        "audio_source",
        "axes",  # 若存在则优先读嵌套 dict，本身不是路径
    }
)

_VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".m4v", ".webm"}

# 展示名（文件名后缀）；未知轴用原 key
_AXIS_LABEL_CN = {
    "closeup": "特写",
    "wide": "全景",
    "mid": "中景",
    "side": "侧机",
    "audience": "观众",
}


def axis_label_cn(axis: str) -> str:
    return _AXIS_LABEL_CN.get(axis, axis)


def _is_video_path(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    return Path(value).suffix.lower() in _VIDEO_SUFFIXES


def resolve_source_axes(
    sources: dict[str, Any],
    *,
    overrides: dict[str, Path] | None = None,
) -> list[tuple[str, Path]]:
    """返回有序 (axis_key, path)。

    优先级：
    1. sources["axes"] 为 dict 时，用其条目（仍按 closeup→wide→其他）
    2. 否则扫顶层：closeup / wide 优先，再及其他以 .mp4 等结尾的路径字段
    3. overrides 覆盖同名轴
    """
    overrides = overrides or {}
    raw: dict[str, str] = {}

    nested = sources.get("axes")
    if isinstance(nested, dict) and nested:
        for k, v in nested.items():
            if _is_video_path(v):
                raw[str(k)] = str(v).strip()
    else:
        for k, v in sources.items():
            if k in _SKIP_KEYS:
                continue
            if _is_video_path(v):
                raw[str(k)] = str(v).strip()

    for k, p in overrides.items():
        if p is not None and str(p).strip():
            raw[str(k)] = str(p)

    if not raw:
        raise FileNotFoundError(
            "sources 中没有任何视频轴（需要 closeup/wide 或 axes{} 内的路径）"
        )

    preferred = ["closeup", "wide"]
    ordered_keys: list[str] = []
    for k in preferred:
        if k in raw:
            ordered_keys.append(k)
    for k in sorted(raw.keys()):
        if k not in ordered_keys:
            ordered_keys.append(k)

    axes: list[tuple[str, Path]] = []
    missing: list[str] = []
    for k in ordered_keys:
        path = Path(raw[k])
        if not path.is_file():
            missing.append(f"{k}={path}")
            continue
        axes.append((k, path))

    if not axes:
        raise FileNotFoundError(
            "视频轴路径均不存在: " + "; ".join(missing or list(raw.keys()))
        )
    if missing:
        # 部分轴缺失：仍导出存在的轴，但调用方可打印警告
        pass
    return axes


def audio_axis_key(axes: list[tuple[str, Path]], preferred: str = "closeup") -> str:
    """预览接版用的音画轴：优先特写。"""
    keys = [k for k, _ in axes]
    if preferred in keys:
        return preferred
    return keys[0]
