# 语义快剪总则（Agent 对话用，不调外部模型 API）

规则 `plan` 只做粗筛。本提示词用于 **人工 / Agent 闸门**：逐段修 `timeline.json`，保证听感完整、不啰嗦。

## 目标

在目标总时长附近，让高光：

1. **语义完整**：不在词/小句中间切断；相邻保留段拼接后能听顺。
2. **叠词只留末次**：「我的，我的…」「我，我，我觉得」「他他」→ 只留最后一次有效表达。
3. **少切**：能并段就并；不要为了镜头碎切破坏句子。
4. **主题优先**：跟本场脚本意图（如 FDE / OPC / 岗位 / 部落型组织 / 流程·洞察革命 / 个人 vs 组织提效）。

## 硬禁止

- 半截收尾（如「叫做懂」「开始慢」「你在流程」「让这组」）。
- 句中硬切定场（听感变成「们在在…」）。
- 为凑时长保留大段铺垫、工具八卦。

## 操作方式

对 `review_script.md` **每一段单独**套用 [`semantic_polish_segment.md`](./semantic_polish_segment.md)：

1. 用 `scripts/dump_words_window.py` 导出本段词表（可含尾后扩窗）。
2. 按模板输出 JSON（replace / merge / extend）。
3. 写回 `timeline.json` 对应片段。
4. 全部段改完后：`scripts/refresh_review.py` 刷新审阅稿 → **人确认** → 再进交付（`cut` + 清单见工作流）。

## 与规则引擎关系

- 不在仓库代码里调用外部模型 HTTP API；判断在 Agent 对话中完成。
- 规则 fillers/shots 可先跑；本步以 Agent 修订为准覆盖 timeline。
- 镜头语言（特写/全景）不在本提示词范围；见 [`shot_director.md`](./shot_director.md)。
