"""ffmpeg 裁切：同一时间轴切双机位；混剪按 shot 选画面，音频固定特写。"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable

from lapi.timeline import Timeline

RunFn = Callable[..., subprocess.CompletedProcess]


def cut_segment_cmd(
    video_path: Path,
    start: float,
    end: float,
    out_path: Path,
    *,
    audio_from: Path | None = None,
) -> list[str]:
    """
    精确裁切一段。若 audio_from 给定且不同于 video，则视频来自 video、音频来自 audio_from
    （用于混剪：画面切机位，音轨始终特写）。
    """
    duration = max(0.01, end - start)
    # 前置粗寻 + 输入后精确；重编码保证 concat 一致
    if audio_from is None or audio_from.resolve() == video_path.resolve():
        return [
            "ffmpeg",
            "-y",
            "-ss",
            f"{start:.3f}",
            "-i",
            str(video_path),
            "-t",
            f"{duration:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(out_path),
        ]

    return [
        "ffmpeg",
        "-y",
        "-ss",
        f"{start:.3f}",
        "-i",
        str(video_path),
        "-ss",
        f"{start:.3f}",
        "-i",
        str(audio_from),
        "-t",
        f"{duration:.3f}",
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-movflags",
        "+faststart",
        str(out_path),
    ]


def concat_cmd(list_path: Path, out_path: Path) -> list[str]:
    return [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_path),
        "-c",
        "copy",
        str(out_path),
    ]


def write_concat_list(paths: list[Path], list_path: Path) -> None:
    list_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for p in paths:
        # concat demuxer 需要转义单引号
        escaped = str(p.resolve()).replace("'", "'\\''")
        lines.append(f"file '{escaped}'")
    list_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_single_camera(
    video_path: Path,
    timeline: Timeline,
    out_path: Path,
    temp_dir: Path,
    *,
    prefix: str,
    run: RunFn = subprocess.run,
) -> Path:
    temp_dir.mkdir(parents=True, exist_ok=True)
    parts: list[Path] = []
    for i, seg in enumerate(timeline.segments):
        part = temp_dir / f"{prefix}_{i:03d}.mp4"
        cmd = cut_segment_cmd(video_path, seg.start, seg.end, part)
        run(cmd, check=True, capture_output=True)
        parts.append(part)

    list_path = temp_dir / f"{prefix}_concat.txt"
    write_concat_list(parts, list_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    run(concat_cmd(list_path, out_path), check=True, capture_output=True)
    return out_path


def render_mixed(
    wide_path: Path,
    closeup_path: Path,
    timeline: Timeline,
    out_path: Path,
    temp_dir: Path,
    *,
    prefix: str = "mix",
    run: RunFn = subprocess.run,
) -> Path:
    """按 shot 选画面；音频始终取 audio_source 对应机位（默认特写）。"""
    temp_dir.mkdir(parents=True, exist_ok=True)
    audio_path = closeup_path if timeline.audio_source == "closeup" else wide_path
    parts: list[Path] = []
    for i, seg in enumerate(timeline.segments):
        video = closeup_path if seg.shot == "closeup" else wide_path
        part = temp_dir / f"{prefix}_{i:03d}.mp4"
        need_remap = video.resolve() != audio_path.resolve()
        cmd = cut_segment_cmd(
            video,
            seg.start,
            seg.end,
            part,
            audio_from=audio_path if need_remap else None,
        )
        run(cmd, check=True, capture_output=True)
        parts.append(part)

    list_path = temp_dir / f"{prefix}_concat.txt"
    write_concat_list(parts, list_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    run(concat_cmd(list_path, out_path), check=True, capture_output=True)
    return out_path


def render_all(
    wide_path: Path,
    closeup_path: Path,
    timeline: Timeline,
    out_dir: Path,
    temp_dir: Path,
    *,
    theme: str,
    run: RunFn = subprocess.run,
) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    wide_out = out_dir / f"{theme}_全景_高光.mp4"
    close_out = out_dir / f"{theme}_特写_高光.mp4"
    mix_out = out_dir / f"{theme}_混剪_高光.mp4"

    render_single_camera(
        wide_path, timeline, wide_out, temp_dir / "wide", prefix="wide", run=run
    )
    render_single_camera(
        closeup_path, timeline, close_out, temp_dir / "closeup", prefix="close", run=run
    )
    render_mixed(
        wide_path,
        closeup_path,
        timeline,
        mix_out,
        temp_dir / "mix",
        prefix="mix",
        run=run,
    )
    return {"wide": wide_out, "closeup": close_out, "mix": mix_out}
