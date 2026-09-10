# 自动导演 · 选段规则

以下参数由规则引擎读取（`key: value` 行）。改这些数字 / 关键词即可调选段，不必改 Python。

pause_gap_seconds: 0.6
min_segment_seconds: 5
max_segment_seconds: 18
sweet_min_seconds: 6
sweet_max_seconds: 14
skip_leading_seconds: 15
merge_gap_seconds: 0.6
target_tolerance_seconds: 8

# 主题核修剪：以主题词为锚，丢掉前后啰嗦铺垫
theme_core_pre_seconds: 4
theme_core_post_seconds: 10

# 小句补全：起止贴到停顿/句末，禁止半截收刀
clause_extend_end_seconds: 6
clause_extend_pre_seconds: 3

# 峰会主题加权（大小写不敏感；命中即大幅加分）
theme_keyword_bonus: 3.5
theme_keywords: FDE,OPC,部落型组织,流程革命,洞察革命,岗位能力,组织提效,个人提效,懂业务,复杂的流程,入企,全栈

# 次优先（企业落地相关，弱于 theme）
secondary_keyword_bonus: 0.6
secondary_keywords: AI落地,组织,岗位,HR,降本增效,吐槽大会,隐含假设

# 降权：偏工具八卦 / 与峰会主线弱相关（有则减分，不禁止）
demote_keyword_penalty: 0.9
demote_keywords: WorkRemotely,GEU,GEO,机场,打字员,键盘

评分启发（供人读 / 未来 LLM）：
- **先保 FDE/OPC 与峰会主线**，再补时长。
- 单段偏短但必须小句完整，禁止「叫做懂」式半截。
- 时长落在 sweet 区间加分；过短或过长减分。
- 语音密度高加分，但不能压过主题命中。
- 落在片头 skip_leading 内的候选大幅减分。
