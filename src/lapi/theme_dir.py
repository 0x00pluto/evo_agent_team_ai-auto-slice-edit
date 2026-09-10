"""temp 工作区目录名：成片区带东八区可读时间戳，抗同名碰撞。

约定：
- 素材枢纽（sources + 合并转写）不打戳，长期稳定。
- 每条成片工作区：`{base}_{YYYY_MM_DD_HH_MM}`；同分钟碰撞追加 `__2`、`__3`。
- CLI `--theme` 对用户仍写短名；output/ 交付目录不打戳。
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

CST = ZoneInfo("Asia/Shanghai")

# base_2026_09_10_17_50 或 base_2026_09_10_17_50__2
_STAMPED_RE = re.compile(
    r"^(?P<base>.+)_(?P<stamp>\d{4}_\d{2}_\d{2}_\d{2}_\d{2})(?:__(?P<n>\d+))?$"
)


def cst_stamp(when: datetime | None = None) -> str:
    """返回 Asia/Shanghai 的 YYYY_MM_DD_HH_MM。"""
    dt = when or datetime.now(CST)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=CST)
    else:
        dt = dt.astimezone(CST)
    return dt.strftime("%Y_%m_%d_%H_%M")


def parse_stamped_name(name: str) -> tuple[str, str, int] | None:
    """若 name 形如 base_戳 或 base_戳__n，返回 (base, stamp, n)；否则 None。

    n=1 表示无后缀；n>=2 为显式碰撞序号。
    """
    m = _STAMPED_RE.match(name)
    if not m:
        return None
    n_raw = m.group("n")
    n = int(n_raw) if n_raw else 1
    return m.group("base"), m.group("stamp"), n


def allocate_temp_dir(
    temp_root: Path,
    base: str,
    *,
    when: datetime | None = None,
    mkdir: bool = True,
) -> Path:
    """创建 `temp_root / {base}_{stamp}`；同分钟已存在则 `__2`、`__3`…"""
    base = base.strip()
    if not base:
        raise ValueError("theme base 不能为空")
    if "/" in base or "\\" in base:
        raise ValueError(f"theme base 不能含路径分隔符: {base!r}")

    temp_root = Path(temp_root)
    temp_root.mkdir(parents=True, exist_ok=True)
    stamp = cst_stamp(when)
    candidate = temp_root / f"{base}_{stamp}"
    n = 2
    while candidate.exists():
        candidate = temp_root / f"{base}_{stamp}__{n}"
        n += 1
    if mkdir:
        candidate.mkdir(parents=True, exist_ok=False)
    return candidate


def resolve_temp_dir(temp_root: Path, theme: str) -> Path:
    """解析 temp 工作区：精确命中；否则短名前缀戳目录取最新；都没有则报错。

    - 精确：`temp_root/theme` 存在（含未打戳枢纽或已写全的戳名）
    - 短名：在 `theme_YYYY_MM_DD_HH_MM` / `theme_…__n` 中取 stamp+n 最大者
    - 枢纽名不会被更短前缀误匹配（要求 stamp 段完整匹配正则）
    """
    theme = theme.strip()
    if not theme:
        raise ValueError("theme 不能为空")
    temp_root = Path(temp_root)
    exact = temp_root / theme
    if exact.is_dir():
        return exact

    matches: list[tuple[str, int, Path]] = []
    if not temp_root.is_dir():
        raise FileNotFoundError(f"找不到 temp 工作区: {exact}")

    for p in temp_root.iterdir():
        if not p.is_dir() or p.name.startswith("."):
            continue
        parsed = parse_stamped_name(p.name)
        if parsed is None:
            continue
        base, stamp, n = parsed
        if base != theme:
            continue
        matches.append((stamp, n, p))

    if not matches:
        raise FileNotFoundError(
            f"找不到 temp 工作区: {exact}（也无 {theme}_YYYY_MM_DD_HH_MM）"
        )
    matches.sort(key=lambda t: (t[0], t[1]))
    return matches[-1][2]
