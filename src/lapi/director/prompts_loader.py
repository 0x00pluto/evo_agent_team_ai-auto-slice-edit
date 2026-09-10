"""加载 prompts/ 下的 Markdown；解析 `key: value` 配置行。"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

_KV = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(.+?)\s*$")


def prompts_dir() -> Path:
    return PROMPTS_DIR


def load_prompt_text(name: str) -> str:
    path = PROMPTS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"缺少导演提示词: {path}")
    return path.read_text(encoding="utf-8")


def parse_kv_config(text: str) -> dict[str, Any]:
    """从 Markdown 中抽取简单 key: value 行。"""
    cfg: dict[str, Any] = {}
    for line in text.splitlines():
        m = _KV.match(line.strip())
        if not m:
            continue
        key, raw = m.group(1), m.group(2).strip()
        if "," in raw and not raw.replace(".", "", 1).replace("-", "", 1).isdigit():
            # 逗号列表（关键词）
            parts = [p.strip() for p in raw.split(",") if p.strip()]
            cfg[key] = parts
            continue
        try:
            if "." in raw:
                cfg[key] = float(raw)
            else:
                cfg[key] = int(raw)
        except ValueError:
            cfg[key] = raw
    return cfg


@lru_cache(maxsize=8)
def load_selection_config() -> dict[str, Any]:
    return parse_kv_config(load_prompt_text("selection.md"))


@lru_cache(maxsize=8)
def load_shot_config() -> dict[str, Any]:
    return parse_kv_config(load_prompt_text("shots.md"))


@lru_cache(maxsize=8)
def load_filler_config() -> dict[str, Any]:
    return parse_kv_config(load_prompt_text("fillers.md"))


def clear_prompt_cache() -> None:
    load_selection_config.cache_clear()
    load_shot_config.cache_clear()
    load_filler_config.cache_clear()
