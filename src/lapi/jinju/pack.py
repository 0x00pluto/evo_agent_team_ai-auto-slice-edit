"""金句交付：多轴备选进 jinju/；推荐收尾焊进三条成片；无第四条。"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Callable

from lapi.cutter import concat_cmd, write_concat_list
from lapi.jinju.export import candidate_filename
from lapi.jinju.schema import load_candidates, jinju_work_dir
from lapi.timeline import load_timeline

RunFn = Callable[..., subprocess.CompletedProcess]

LEGACY_PREVIEW_MARK = "含推荐收尾"


def narrative_dir(temp_theme_dir: Path) -> Path:
    return Path(temp_theme_dir) / "narrative"


def is_jinju_stinger_mp4(path: Path) -> bool:
    """多轴金句条：*.mp4 且不是历史「含推荐收尾」预览。"""
    if not path.is_file() or path.suffix.lower() != ".mp4":
        return False
    return LEGACY_PREVIEW_MARK not in path.name


def list_jinju_stinger_mp4s(src: Path) -> list[Path]:
    return sorted(p for p in src.glob("*.mp4") if is_jinju_stinger_mp4(p))


def remove_legacy_preview_files(*dirs: Path) -> list[Path]:
    removed: list[Path] = []
    for d in dirs:
        if not d or not Path(d).is_dir():
            continue
        for p in Path(d).glob(f"*{LEGACY_PREVIEW_MARK}*"):
            if p.is_file():
                p.unlink()
                removed.append(p)
    return removed


def copy_jinju_editor_bundle(src: Path, dest: Path) -> int:
    """把剪辑用金句清单拷到 dest（仅 review.md + 多轴条）。返回条数。"""
    dest.mkdir(parents=True, exist_ok=True)
    review = src / "review.md"
    if not review.is_file():
        raise FileNotFoundError(f"缺 review.md: {review}")
    shutil.copy2(review, dest / "review.md")
    stingers = list_jinju_stinger_mp4s(src)
    if not stingers:
        raise FileNotFoundError(f"金句目录无多轴 mp4（先 export）: {src}")
    for p in stingers:
        shutil.copy2(p, dest / p.name)
    return len(stingers)


def resolve_jinju_work_src(
    temp_theme_dir: Path,
    output_dir: Path | None = None,
) -> Path | None:
    """优先 temp/<theme>/jinju；否则 output/jinju。"""
    src = jinju_work_dir(temp_theme_dir)
    if src.is_dir() and (
        (src / "candidates.json").is_file()
        or (src / "review.md").is_file()
        or list_jinju_stinger_mp4s(src)
    ):
        return src
    if output_dir is not None:
        alt = Path(output_dir) / "jinju"
        if alt.is_dir() and (
            (alt / "review.md").is_file() or list_jinju_stinger_mp4s(alt)
        ):
            return alt
    return None


def snapshot_narrative_bases(
    theme: str,
    temp_theme_dir: Path,
    *,
    video_paths: dict[str, Path] | None = None,
    output_dir: Path | None = None,
    force: bool = False,
) -> Path:
    """把叙事三片底片写入 temp/<theme>/narrative/。

    force=True（dualcam cut 后）始终覆盖；否则仅缺文件时从 output 补齐。
    """
    dest = narrative_dir(temp_theme_dir)
    dest.mkdir(parents=True, exist_ok=True)
    names = {
        "closeup": f"{theme}_特写_高光.mp4",
        "wide": f"{theme}_全景_高光.mp4",
        "mix": f"{theme}_混剪_高光.mp4",
    }
    for label, name in names.items():
        target = dest / name
        if target.is_file() and not force:
            continue
        src: Path | None = None
        if video_paths and label in video_paths and Path(video_paths[label]).is_file():
            src = Path(video_paths[label])
        elif output_dir is not None:
            cand = Path(output_dir) / name
            if cand.is_file():
                src = cand
        if src is None:
            if force or not target.is_file():
                raise FileNotFoundError(
                    f"叙事底片缺失 ({label}): 需 output 或 cut 路径提供 {name}"
                )
            continue
        shutil.copy2(src, target)
    return dest


def _find_recommended_stingers(
    jinju_src: Path, theme: str
) -> tuple[Path, Path | None]:
    """返回 (推荐特写条, 推荐全景条|None)。"""
    doc = load_candidates(jinju_src / "candidates.json")
    rec = doc.candidates[doc.recommended]
    close_name = candidate_filename(doc.recommended, rec, "closeup")
    wide_name = candidate_filename(doc.recommended, rec, "wide")
    close_p = jinju_src / close_name
    wide_p = jinju_src / wide_name
    if not close_p.is_file():
        # 兼容仅特写命名残留
        alts = [
            p
            for p in list_jinju_stinger_mp4s(jinju_src)
            if p.name.startswith(f"{doc.recommended:02d}_") and "特写" in p.name
        ]
        if not alts:
            raise FileNotFoundError(f"缺推荐特写金句条: {close_p}")
        close_p = alts[0]
    wide_out = wide_p if wide_p.is_file() else None
    return close_p, wide_out


def bake_recommended_ending(
    theme: str,
    temp_theme_dir: Path,
    output_dir: Path,
    *,
    run: RunFn = subprocess.run,
) -> dict[str, Path]:
    """从 narrative 底片 + 推荐金句 concat，覆盖 output 三条成片。"""
    narr = narrative_dir(temp_theme_dir)
    jinju_src = jinju_work_dir(temp_theme_dir)
    close_stinger, wide_stinger = _find_recommended_stingers(jinju_src, theme)

    work = jinju_src / "_bake"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    mapping = [
        ("closeup", f"{theme}_特写_高光.mp4", close_stinger),
        ("wide", f"{theme}_全景_高光.mp4", wide_stinger or close_stinger),
        ("mix", f"{theme}_混剪_高光.mp4", close_stinger),
    ]
    out: dict[str, Path] = {}
    for label, name, stinger in mapping:
        base = narr / name
        if not base.is_file():
            raise FileNotFoundError(f"缺叙事底片: {base}")
        dest = Path(output_dir) / name
        list_path = work / f"{label}_concat.txt"
        write_concat_list([base, stinger], list_path)
        # 写到 staging 再替换，避免源目同一文件
        tmp_out = work / name
        run(concat_cmd(list_path, tmp_out), check=True, capture_output=True)
        shutil.copy2(tmp_out, dest)
        out[label] = dest
    return out


def append_jinju_cue_to_highlight_srt(
    temp_theme_dir: Path,
    output_dir: Path | None = None,
) -> dict[str, Path]:
    """按横竖屏重生成片轴字幕，并追加推荐金句（格式化后）。"""
    from lapi.captions.write import write_caption_set

    temp_theme_dir = Path(temp_theme_dir)
    tl = load_timeline(temp_theme_dir / "timeline.json")
    doc = load_candidates(jinju_work_dir(temp_theme_dir) / "candidates.json")
    rec = doc.candidates[doc.recommended]
    narr_dur = tl.total_duration()
    end = narr_dur + rec.duration
    return write_caption_set(
        temp_theme_dir,
        output_dir=output_dir,
        jinju_quote=rec.quote,
        jinju_start=narr_dur,
        jinju_end=end,
        remove_legacy_highlight=True,
    )


def pack_jinju(
    temp_theme_dir: Path,
    output_theme_dir: Path,
    *,
    run: RunFn = subprocess.run,
    bake: bool = True,
) -> Path:
    """组装 jinju/ 备选 + 把推荐收尾焊进三条成片。

    - output/<theme>/jinju/：review.md + 多轴条
    - 覆盖 output 三片 = narrative + 推荐轴
    - 删除一切「含推荐收尾」第四条
    """
    src = jinju_work_dir(temp_theme_dir)
    if not src.is_dir():
        raise FileNotFoundError(f"缺金句工作区: {src}")
    if not (src / "candidates.json").is_file():
        raise FileNotFoundError(f"缺 candidates.json: {src / 'candidates.json'}")
    if not (src / "review.md").is_file():
        raise FileNotFoundError(f"缺 review.md: {src / 'review.md'}")

    theme = output_theme_dir.name
    output_theme_dir = Path(output_theme_dir)
    output_theme_dir.mkdir(parents=True, exist_ok=True)

    # 先快照叙事底片（仅缺时从 output 拷；已有则不动，保证可重入）
    snapshot_narrative_bases(
        theme, temp_theme_dir, output_dir=output_theme_dir, force=False
    )

    dest = output_theme_dir / "jinju"
    staging = (
        output_theme_dir.parent / f".{output_theme_dir.name}.jinju_staging"
    )
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    try:
        copy_jinju_editor_bundle(src, staging)
        if dest.exists():
            shutil.rmtree(dest)
        staging.rename(dest)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        raise

    if bake:
        bake_recommended_ending(
            theme, temp_theme_dir, output_theme_dir, run=run
        )
        append_jinju_cue_to_highlight_srt(temp_theme_dir, output_theme_dir)

    remove_legacy_preview_files(output_theme_dir, dest, src)

    return dest


def restore_jinju_into_staging(
    staging: Path,
    temp_theme_dir: Path,
    output_dir: Path | None = None,
    *,
    theme: str | None = None,
) -> bool:
    """双机位 pack 重建根目录时回填 jinju/（仅剪辑清单，无第四条预览）。"""
    src = resolve_jinju_work_src(temp_theme_dir, output_dir)
    if src is None:
        return False

    dest = staging / "jinju"
    if dest.exists():
        shutil.rmtree(dest)
    try:
        copy_jinju_editor_bundle(src, dest)
    except FileNotFoundError:
        if dest.exists():
            shutil.rmtree(dest, ignore_errors=True)
        return False
    return True
