"""语气词快剪：在内容拍内按词级时间戳挖掉口癖。"""

from __future__ import annotations

import re
from typing import Any

_PUNCT = re.compile(r"^[\s\W_]+|[\s\W_]+$", re.UNICODE)


def _norm(text: str) -> str:
    t = _PUNCT.sub("", str(text or ""))
    return t.strip().lower()


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x) for x in value]
    return [str(value)]


def _words_in_range(
    words: list[dict[str, Any]], start: float, end: float
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for w in words:
        try:
            ws, we = float(w["start"]), float(w["end"])
        except (KeyError, TypeError, ValueError):
            continue
        if we < start - 1e-6 or ws > end + 1e-6:
            continue
        text = str(w.get("text") or "")
        if w.get("type") == "spacing" or not text.strip():
            continue
        out.append({"text": text, "start": ws, "end": we, "norm": _norm(text)})
    return out


def _is_content_token(norm: str, filler_set: set[str]) -> bool:
    if not norm or norm in filler_set:
        return False
    # 单字标点已清；长度≥2 视为潜在实词
    return len(norm) >= 2


def _should_cut(
    i: int,
    seq: list[dict[str, Any]],
    filler_set: set[str],
    demonstratives: set[str],
    then_keep: list[str],
) -> bool:
    w = seq[i]
    n = w["norm"]
    if not n or n not in filler_set:
        return False

    # 「这个/那个」+ 实词 → 保护
    if n in demonstratives and i + 1 < len(seq):
        nxt = seq[i + 1]["norm"]
        if _is_content_token(nxt, filler_set):
            return False

    # 「然后」+ 配置的承接前缀 → 保留；否则作口癖切除
    if n in ("然后", "然后呢", "然后就") and i + 1 < len(seq):
        rest = "".join(x["norm"] for x in seq[i + 1 : i + 4])
        for p in then_keep:
            if rest.startswith(p.lower()):
                return False

    return True


def _is_punct_only(norm: str, raw: str) -> bool:
    if not raw.strip():
        return True
    if not norm:
        return True
    # 纯标点
    return all(not (ch.isalnum() or ("\u4e00" <= ch <= "\u9fff")) for ch in raw.strip())


def _stutter_cut_flags(
    seq: list[dict[str, Any]],
    *,
    max_token_len: int,
    max_keep: int,
) -> list[bool]:
    """连续相同短词（中间可夹纯标点）：前面的标切除，只留最后 max_keep 个。"""
    flags = [False] * len(seq)

    # 有效内容下标序列（跳过纯标点）
    content_idx = [
        i
        for i, w in enumerate(seq)
        if w["norm"] and not _is_punct_only(w["norm"], w["text"])
    ]

    i = 0
    while i < len(content_idx):
        ci = content_idx[i]
        n = seq[ci]["norm"]
        if len(n) > max_token_len:
            i += 1
            continue
        j = i + 1
        while j < len(content_idx) and seq[content_idx[j]]["norm"] == n:
            j += 1
        run = j - i
        if run > max_keep:
            for k in range(i, j - max_keep):
                flags[content_idx[k]] = True
                # 夹在中间的标点一并切掉
                a, b = content_idx[k], content_idx[k + 1] if k + 1 < j else content_idx[k]
                for m in range(a + 1, b):
                    if _is_punct_only(seq[m]["norm"], seq[m]["text"]):
                        flags[m] = True
        i = j

    # 「我」+「觉」… 组成「我觉得」：短词后紧跟同开头的拆开字
    for i in range(len(content_idx) - 1):
        ci = content_idx[i]
        ni = content_idx[i + 1]
        n = seq[ci]["norm"]
        nxt = seq[ni]["norm"]
        if not n or len(n) > max_token_len:
            continue
        # 我 + 觉（得）
        if len(n) == 1 and nxt and n == nxt[0] and len(nxt) == 1:
            # 向后拼 我觉得
            glued = n + nxt
            k = i + 2
            while k < len(content_idx) and len(glued) < 4:
                glued += seq[content_idx[k]]["norm"]
                k += 1
            if glued.startswith(n) and len(glued) > len(n) and n in ("我", "他", "那", "这"):
                # 若后面是 我觉得 结构，切掉多余的重复 我（已在上面 run 处理）
                pass
        if len(n) <= max_token_len and len(nxt) > len(n) and nxt.startswith(n):
            flags[ci] = True
    return flags


def cut_fillers(
    words: list[dict[str, Any]],
    start: float,
    end: float,
    cfg: dict[str, Any],
) -> tuple[list[tuple[float, float]], int, float]:
    """
    返回 (保留区间列表, 切除次数, 切除总秒数)。
    保留区间落在 [start, end] 内，已按时间排序且不重叠。
    """
    pad_before = float(cfg.get("pad_before_ms", 50)) / 1000.0
    pad_after = float(cfg.get("pad_after_ms", 60)) / 1000.0
    min_keep = float(cfg.get("min_keep_seconds", 0.45))
    min_gap = float(cfg.get("min_gap_to_cut_seconds", 0.12))
    stutter_len = int(cfg.get("stutter_max_token_len", 2))
    stutter_keep = int(cfg.get("stutter_max_keep", 1))

    filler_set = {_norm(x) for x in _as_list(cfg.get("filler_words")) if _norm(x)}
    demonstratives = {
        _norm(x) for x in _as_list(cfg.get("demonstrative_protect")) if _norm(x)
    }
    then_keep = [_norm(x) for x in _as_list(cfg.get("then_keep_prefixes")) if _norm(x)]

    seq = _words_in_range(words, start, end)
    if not seq:
        return [(start, end)], 0, 0.0

    cut_flags = [
        _should_cut(i, seq, filler_set, demonstratives, then_keep) for i in range(len(seq))
    ]
    stutter_flags = _stutter_cut_flags(
        seq, max_token_len=stutter_len, max_keep=stutter_keep
    )
    cut_flags = [a or b for a, b in zip(cut_flags, stutter_flags)]

    # 合并连续切除为区间
    raw_cuts: list[tuple[float, float]] = []
    i = 0
    while i < len(seq):
        if not cut_flags[i]:
            i += 1
            continue
        j = i
        while j < len(seq) and cut_flags[j]:
            j += 1
        c0 = max(start, seq[i]["start"] - pad_before)
        c1 = min(end, seq[j - 1]["end"] + pad_after)
        # 不把 pad 吃进后面要保留的词（避免「我」切掉时吞掉「我觉得」）
        if j < len(seq):
            c1 = min(c1, seq[j]["start"])
        if i > 0:
            c0 = max(c0, seq[i - 1]["end"])
        if c1 - c0 >= min_gap:
            raw_cuts.append((c0, c1))
        i = j

    # 合并重叠/相邻切除
    merged: list[tuple[float, float]] = []
    for c0, c1 in sorted(raw_cuts):
        if not merged or c0 > merged[-1][1] + 1e-6:
            merged.append((c0, c1))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], c1))

    # 从 [start,end] 挖洞得到保留
    keeps: list[tuple[float, float]] = []
    cursor = start
    cut_seconds = 0.0
    for c0, c1 in merged:
        if c0 > cursor + 1e-6:
            keeps.append((cursor, c0))
        cut_seconds += max(0.0, c1 - c0)
        cursor = max(cursor, c1)
    if end > cursor + 1e-6:
        keeps.append((cursor, end))

    # 过短保留片并回（并入相邻，即取消该处切除）
    if not keeps:
        return [(start, end)], 0, 0.0

    refined: list[tuple[float, float]] = []
    for k0, k1 in keeps:
        if k1 - k0 >= min_keep:
            refined.append((k0, k1))
        elif refined:
            # 并入上一段：等于不切中间洞 → 扩展上一段 end
            refined[-1] = (refined[-1][0], k1)
        else:
            # 开头过短：并到下一段（稍后）
            refined.append((k0, k1))

    # 再滤一次过短
    final: list[tuple[float, float]] = []
    for k0, k1 in refined:
        if k1 - k0 >= min_keep * 0.5:
            final.append((k0, k1))

    if not final:
        return [(start, end)], 0, 0.0

    # 过碎保留片：若与邻段间隔很小，跨缝合并（撤回过碎语气切除）
    coalesced: list[tuple[float, float]] = [final[0]]
    for k0, k1 in final[1:]:
        prev0, prev1 = coalesced[-1]
        gap = k0 - prev1
        if gap <= 0.35 and (
            (k1 - k0) < min_keep * 1.5 or (prev1 - prev0) < min_keep * 1.5
        ):
            coalesced[-1] = (prev0, k1)
        else:
            coalesced.append((k0, k1))

    # 重算切除：总窗减去保留
    keep_sec = sum(b - a for a, b in coalesced)
    cut_seconds = max(0.0, (end - start) - keep_sec)
    return coalesced, len(merged), cut_seconds
