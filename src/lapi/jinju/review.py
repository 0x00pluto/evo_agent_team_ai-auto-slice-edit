"""金句审阅稿：给人听选推荐压轴。"""

from __future__ import annotations

from pathlib import Path

from lapi.jinju.schema import JinjuCandidates


def _fmt_tc(seconds: float) -> str:
    s = max(0.0, float(seconds))
    m = int(s // 60)
    rem = s - m * 60
    return f"{m:02d}:{rem:06.3f}"


def render_jinju_review(doc: JinjuCandidates) -> str:
    lines: list[str] = [
        f"# 金句筛选审阅 · {doc.theme or '（未命名）'}",
        "",
        f"- 候选数: **{len(doc.candidates)}**",
        f"- 推荐压轴下标: **{doc.recommended}**（从 0 起；人可改 `candidates.json`）",
        "- 听感: `falling`=降调落地 · `punchy`=铿锵有力",
        "- 导出：**sources 有几轴出几轴**同时间码备选条",
        "- **成片三条（特写/全景/混剪）末尾已焊入推荐金句**；要换结尾，用本目录对应轴条替换最后一截即可",
        "",
    ]
    if doc.notes:
        lines.extend([f"> {doc.notes}", ""])

    lines.extend(
        [
            "| # | 时间码 | 时长 | delivery | shot | reason | 口播 |",
            "|---|--------|------|----------|------|--------|------|",
        ]
    )
    for i, c in enumerate(doc.candidates):
        mark = " ★推荐" if i == doc.recommended else ""
        lines.append(
            f"| {i}{mark} | {_fmt_tc(c.start)} → {_fmt_tc(c.end)} | "
            f"{c.duration:.1f}s | `{c.delivery}` | `{c.shot}` | "
            f"{c.reason or '—'} | {c.quote} |"
        )

    lines.extend(["", "## 分段正文", ""])
    for i, c in enumerate(doc.candidates):
        mark = " ★推荐压轴（已焊进三条成片末尾）" if i == doc.recommended else ""
        lines.extend(
            [
                f"### {i}. {_fmt_tc(c.start)} → {_fmt_tc(c.end)}"
                f"（`{c.delivery}` / `{c.shot}`）{mark}",
                "",
                f"- reason: {c.reason or '—'}",
                f"- 摘录: {c.quote}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_jinju_review(doc: JinjuCandidates, path: Path | str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_jinju_review(doc), encoding="utf-8")
    return path
