"""成片轴字幕格式化：断句符→空格；引号书名号括号保留；按词边界切 cue。"""

from __future__ import annotations

import re
from typing import Any

# 断句 / 停顿 → 空格（画面字幕里逗号句号会怪）
_BREAK_PUNCT = (
    "，,。．.!！？?、；;：:…"
    "—－–-~～·・"
)
# 多字符省略
_BREAK_MULTI = ("......", "…", "...", "--")

_BREAK_TRANS = str.maketrans({c: " " for c in _BREAK_PUNCT})
_SPACE_RE = re.compile(r"\s+")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def replace_break_punct_with_space(text: str) -> str:
    """只替换断句/停顿符；保留引号、书名号、括号。"""
    s = text or ""
    for m in _BREAK_MULTI:
        s = s.replace(m, " ")
    s = s.translate(_BREAK_TRANS)
    return _SPACE_RE.sub(" ", s).strip()


def display_len(text: str) -> int:
    """计字：不计空格；保留的引号括号计入。"""
    return sum(1 for c in text if not c.isspace())


def join_caption_parts(parts: list[str]) -> str:
    """CJK 词之间不加空格；断句空格 / 拉丁词保留空格。"""
    if not parts:
        return ""
    out = parts[0]
    for p in parts[1:]:
        if not p:
            continue
        if out.endswith(" ") or p.startswith(" "):
            out = out + p
        elif _CJK_RE.search(out[-1] or "") and _CJK_RE.search(p[0] or ""):
            out = out + p
        else:
            out = out + " " + p
    return _SPACE_RE.sub(" ", out).strip()


def _ts(seconds: float) -> str:
    ms = int(round(max(0.0, seconds) * 1000))
    h, rem = divmod(ms, 3600_000)
    m, rem = divmod(rem, 60_000)
    s, milli = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{milli:03d}"


def pack_words_to_cues(
    words: list[dict[str, Any]],
    max_chars: int,
) -> list[tuple[float, float, str]]:
    """按词边界打包 cue；不截断单个 STT 词。

    每个 word 需含 text/start/end（成片轴秒）。
    """
    cues: list[tuple[float, float, str]] = []
    buf_parts: list[str] = []
    cue_start: float | None = None
    cue_end: float = 0.0

    def flush() -> None:
        nonlocal buf_parts, cue_start
        if not buf_parts or cue_start is None:
            return
        text = join_caption_parts(buf_parts)
        if text:
            cues.append((cue_start, cue_end, text))
        buf_parts = []
        cue_start = None

    for w in words:
        raw = str(w.get("text") or "")
        cleaned = replace_break_punct_with_space(raw)
        if not cleaned:
            # 纯断句符：可作收束点
            if buf_parts:
                flush()
            continue
        try:
            w_start = float(w["start"])
            w_end = float(w["end"])
        except (KeyError, TypeError, ValueError):
            continue

        # 词尾原带断句意图：cleaned 后若原词以断句符结尾，flush 偏好在本词后
        stripped = raw.strip()
        had_break_end = bool(stripped) and stripped[-1] in _BREAK_PUNCT

        next_len = display_len(cleaned)
        cur_len = display_len(join_caption_parts(buf_parts)) if buf_parts else 0

        if cue_start is None:
            cue_start = w_start
            buf_parts = [cleaned]
            cue_end = w_end
            if had_break_end or next_len >= max_chars:
                flush()
            continue

        if cur_len + next_len > max_chars and buf_parts:
            flush()
            cue_start = w_start
            buf_parts = [cleaned]
            cue_end = w_end
            if had_break_end or next_len >= max_chars:
                flush()
            continue

        buf_parts.append(cleaned)
        cue_end = w_end
        if had_break_end:
            flush()

    flush()
    return cues


def cues_to_srt(cues: list[tuple[float, float, str]]) -> str:
    lines: list[str] = []
    for i, (s, e, text) in enumerate(cues, start=1):
        lines.append(str(i))
        lines.append(f"{_ts(s)} --> {_ts(e)}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


def words_to_caption_srt(words: list[dict[str, Any]], max_chars: int) -> str:
    return cues_to_srt(pack_words_to_cues(words, max_chars))


def format_quote_as_cues(
    quote: str,
    start: float,
    end: float,
    max_chars: int,
) -> list[tuple[float, float, str]]:
    """金句 quote 无词级时间时：去断句符后按空格词包 cue，时间均分。"""
    text = replace_break_punct_with_space(quote)
    if not text:
        return []
    tokens = [t for t in text.split(" ") if t]
    if not tokens:
        return []

    def hard_split_token(tok: str) -> list[str]:
        """单 token 仍超长时按字硬切（极少见）。"""
        chars = [c for c in tok if not c.isspace()]
        if not chars:
            return []
        parts: list[str] = []
        for i in range(0, len(chars), max_chars):
            parts.append("".join(chars[i : i + max_chars]))
        return parts

    expanded: list[str] = []
    for tok in tokens:
        if display_len(tok) <= max_chars:
            expanded.append(tok)
        else:
            expanded.extend(hard_split_token(tok))

    chunks: list[str] = []
    buf: list[str] = []
    for tok in expanded:
        trial = join_caption_parts(buf + [tok])
        if buf and display_len(trial) > max_chars:
            chunks.append(join_caption_parts(buf))
            buf = [tok]
        else:
            buf.append(tok)
    if buf:
        chunks.append(join_caption_parts(buf))
    chunks = [c for c in chunks if c]
    if not chunks:
        return []
    dur = max(0.01, end - start)
    step = dur / len(chunks)
    out: list[tuple[float, float, str]] = []
    for i, c in enumerate(chunks):
        s = start + i * step
        e = start + (i + 1) * step if i < len(chunks) - 1 else end
        out.append((s, e, c))
    return out
