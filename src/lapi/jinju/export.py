"""金句导出：按 sources 有几轴切几轴同时间码素材（焊尾在 pack）。"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Callable

from lapi.cutter import cut_segment_cmd
from lapi.jinju.review import write_jinju_review
from lapi.jinju.schema import JinjuCandidates, JinjuCandidate, jinju_work_dir
from lapi.jinju.sources import axis_label_cn, resolve_source_axes

RunFn = Callable[..., subprocess.CompletedProcess]


def _slugify(text: str, fallback: str) -> str:
    s = re.sub(r"\s+", "", text)
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "", s, flags=re.UNICODE)
    s = s[:24] if s else fallback
    return s or fallback


def candidate_stem(index: int, c: JinjuCandidate) -> str:
    slug = c.slug or _slugify(c.quote, f"jinju{index:02d}")
    return f"{index:02d}_{slug}"


def candidate_filename(index: int, c: JinjuCandidate, axis: str) -> str:
    """多轴文件名：00_slug_特写.mp4 / 00_slug_全景.mp4。"""
    return f"{candidate_stem(index, c)}_{axis_label_cn(axis)}.mp4"


def export_stingers(
    axes: list[tuple[str, Path]],
    doc: JinjuCandidates,
    out_dir: Path,
    *,
    run: RunFn = subprocess.run,
) -> dict[str, list[Path]]:
    """按 candidates × 每一路源片切同时间码金句条。

    返回 {axis_key: [path_per_candidate, ...]}。
    """
    if not axes:
        raise ValueError("axes 不能为空")
    out_dir.mkdir(parents=True, exist_ok=True)
    by_axis: dict[str, list[Path]] = {k: [] for k, _ in axes}
    for i, c in enumerate(doc.candidates):
        for axis, video_path in axes:
            name = candidate_filename(i, c, axis)
            out = out_dir / name
            cmd = cut_segment_cmd(video_path, c.start, c.end, out)
            run(cmd, check=True, capture_output=True)
            by_axis[axis].append(out)
    return by_axis


def _clear_old_stinger_mp4s(work: Path) -> None:
    """重导前清掉旧金句条，避免残留误导。"""
    for p in work.glob("*.mp4"):
        if p.is_file():
            p.unlink()


def export_all(
    *,
    theme: str,
    sources: dict,
    doc: JinjuCandidates,
    temp_theme_dir: Path,
    axis_overrides: dict[str, Path] | None = None,
    run: RunFn = subprocess.run,
) -> dict[str, Path | list[Path] | dict[str, list[Path]]]:
    """写出 temp/<theme>/jinju/ 下多轴单条、review.md（不含第四条成片）。"""
    axes = resolve_source_axes(sources, overrides=axis_overrides)
    work = jinju_work_dir(temp_theme_dir)
    work.mkdir(parents=True, exist_ok=True)
    _clear_old_stinger_mp4s(work)
    doc.save(work / "candidates.json")
    review_path = write_jinju_review(doc, work / "review.md")

    by_axis = export_stingers(axes, doc, work, run=run)
    flat: list[Path] = []
    for paths in by_axis.values():
        flat.extend(paths)

    axes_manifest = work / "axes.txt"
    axes_manifest.write_text(
        "\n".join(f"{k}\t{axis_label_cn(k)}\t{p}" for k, p in axes) + "\n",
        encoding="utf-8",
    )
    return {
        "axes": by_axis,
        "stingers": flat,
        "review": review_path,
        "candidates": work / "candidates.json",
        "axes_manifest": axes_manifest,
    }
