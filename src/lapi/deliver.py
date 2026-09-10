"""组装干净交付包：output/<theme>/ 只含可上传清单。"""

from __future__ import annotations

import shutil
from pathlib import Path

from lapi.jinju.pack import restore_jinju_into_staging


def deliverable_video_names(theme: str) -> list[str]:
    return [
        f"{theme}_特写_高光.mp4",
        f"{theme}_全景_高光.mp4",
        f"{theme}_混剪_高光.mp4",
    ]


def deliverable_doc_names() -> list[str]:
    """上传清单中的文稿（timeline.json 仅留 temp，不进 output）。"""
    return ["review_script.md", "highlight_竖屏.srt", "highlight_横屏.srt"]


def pack_deliver(
    temp_dir: Path,
    output_dir: Path,
    theme: str,
    *,
    video_paths: dict[str, Path] | None = None,
) -> Path:
    """重建 output_dir 为干净交付包。

    - 文稿从 temp_dir 拷贝 review_script.md / highlight_竖屏.srt / highlight_横屏.srt
    - timeline.json 须存在于 temp（供再 cut），但不拷进 output
    - 视频：优先用 video_paths（cut 刚写出的路径），否则从 output_dir 已有文件搬入 staging
    - 若存在金句子包：回填 output/.../jinju/（仅多轴条+review；无第四条预览）
    """
    docs = deliverable_doc_names()
    videos = deliverable_video_names(theme)

    if not (temp_dir / "timeline.json").is_file():
        raise FileNotFoundError(
            f"交付缺工作区 timeline（应在 temp/{temp_dir.name}/timeline.json，供再 cut）"
        )

    missing_docs = [n for n in docs if not (temp_dir / n).is_file()]
    if missing_docs:
        raise FileNotFoundError(
            f"交付缺文稿（应在 temp/{temp_dir.name}/）: {', '.join(missing_docs)}"
        )

    resolved_videos: dict[str, Path] = {}
    if video_paths:
        label_to_name = {
            "closeup": f"{theme}_特写_高光.mp4",
            "wide": f"{theme}_全景_高光.mp4",
            "mix": f"{theme}_混剪_高光.mp4",
        }
        for label, name in label_to_name.items():
            p = video_paths.get(label)
            if p is None or not Path(p).is_file():
                raise FileNotFoundError(f"交付缺视频 ({label}): {p}")
            resolved_videos[name] = Path(p)
    else:
        for name in videos:
            # 先看 output，再看 temp（兼容回填前误放位置）
            for base in (output_dir, temp_dir):
                cand = base / name
                if cand.is_file():
                    resolved_videos[name] = cand
                    break
            else:
                raise FileNotFoundError(
                    f"交付缺视频: {name}（在 output 与 temp 均未找到）"
                )

    staging = output_dir.parent / f".{output_dir.name}.pack_staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    try:
        for name in docs:
            shutil.copy2(temp_dir / name, staging / name)
        for name, src in resolved_videos.items():
            dest = staging / name
            if src.resolve() == dest.resolve():
                continue
            # 若源已在即将被清空的 output_dir 内，先拷到 staging
            shutil.copy2(src, dest)

        restore_jinju_into_staging(
            staging, temp_dir, output_dir, theme=theme
        )

        if output_dir.exists():
            shutil.rmtree(output_dir)
        staging.rename(output_dir)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        raise

    return output_dir
