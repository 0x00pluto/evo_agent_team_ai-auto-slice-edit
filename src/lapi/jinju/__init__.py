"""金句筛选（京剧口语 = 金句）：独立于双机位叙事初剪。"""

from __future__ import annotations

from lapi.jinju.export import export_all, export_stingers
from lapi.jinju.pack import pack_jinju, snapshot_narrative_bases
from lapi.jinju.schema import (
    JinjuCandidate,
    JinjuCandidates,
    load_candidates,
    validate_candidates,
)
from lapi.jinju.sources import resolve_source_axes

__all__ = [
    "JinjuCandidate",
    "JinjuCandidates",
    "export_all",
    "export_stingers",
    "load_candidates",
    "pack_jinju",
    "resolve_source_axes",
    "snapshot_narrative_bases",
    "validate_candidates",
]

