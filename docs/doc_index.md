# Document index

## Index

- `docs/builtin-workflows/post-task-reflect.md`: 任务后反思（白痴指数 → 删 → 程序化 → 鲁棒 → 加速）；用户明确要求时触发，不自动跑
- `docs/builtin-workflows/extract-experience.md`: 提取经验 → 项目无关最佳实践；用户明确要求时触发；落盘须问或读 experience_target，默认本仓 docs/best-practices/
- `docs/builtin-workflows/publish-evo-agent-pack.md`: 仅首次 / 改合同时发布或核对 evo_agent_pack.json 工牌；日常发版勿进门；打 tag 改走 cut-release-tag；不做安装器
- `docs/builtin-workflows/cut-release-tag.md`: 日常发版唯一入口；汇总变更 → upgrades → 对齐 version → tag → 推送 → gh 或网页建 Release；major 须人指定
- `docs/workflows/_TEMPLATE.md`: 业务 workflow 六段骨架；新建业务工作流时复制并改名，写完后删掉本行或改成真实条目
- `docs/workflows/choose-edit-style.md`: 开剪选型入口（峰会高光 / 新建手法 / 不用模板）；机位不写死；访谈 A/B 仅占名
- `docs/workflows/summit-highlight.md`: 峰会高光手法总览；编排 dualcam + jinju；机位=用户片源路数；含仅补金句路径
- `docs/workflows/dualcam-auto-highlight.md`: 峰会手法叙事子步骤；plan → 语义快剪 → 镜头导演 → cut；机位随 sources；工作文件仅 temp
- `docs/workflows/jinju-select.md`: 峰会手法金句子步骤（京剧=金句）；有几轴出几轴；推荐收尾焊进成片；无第四条成片；candidates/axes 仅 temp
- `src/lapi/jinju/prompts/select.md`: 金句筛选总则（独立上屏、falling|punchy、多轴同码；Agent 对话用）
- `src/lapi/jinju/prompts/select_segment.md`: 单条金句评分模板（keep/drop JSON）
- `src/lapi/director/prompts/semantic_polish.md`: 语义快剪总则（叠词末次、禁半截、少切；Agent 对话用，不嵌模型 API）
- `src/lapi/director/prompts/semantic_polish_segment.md`: 单段语义快剪模板（输入词表 → 输出 replace/merge JSON）
- `src/lapi/director/prompts/shot_director.md`: 镜头导演总则（仅 closeup|wide；主特写辅全景；Agent 对话用）
- `src/lapi/director/prompts/shot_director_segment.md`: 单段镜头导演模板（keep/replace JSON）
- `src/lapi/director/prompts/highlight_srt_polish.md`: 高光字幕别字纠错（横竖屏各一份；禁改时间码/cue 结构；Agent 对话用）
- `src/lapi/highlight_srt.py`: transcript+timeline → 成片轴词映射；兼容入口写出横竖屏字幕
- `src/lapi/captions/`: 横竖屏字幕模块（竖≤14 / 横≤20；断句符→空格；与成片轴对齐）
