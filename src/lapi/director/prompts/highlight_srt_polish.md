# 高光字幕纠错（Agent 对话用，不调外部模型 API）

`cut` / `ensure_highlight_srt` / 金句 `pack` 会从 `transcript.json` + `timeline.json` **映射**出与成片轴严格对齐的横竖屏草稿：

- `temp/<theme>/highlight_竖屏.srt`（≤14 字/cue）
- `temp/<theme>/highlight_横屏.srt`（≤20 字/cue）

断句标点已换成空格；引号/书名号/括号保留。本提示词只做**正文错字/别字**修正。  
**不要**再写或保留旧的 `highlight.srt`。

## 硬约束（对齐优先）

1. **禁止改任何 cue 的时间码行**（`HH:MM:SS,mmm --> HH:MM:SS,mmm` 一字不动）。
2. **禁止增删/合并/拆分 cue**：序号与 cue 条数保持不变。
3. **禁止臆造未说出的词**；只改明显 ASR 误识（同音别字、专有名词大小写/拼写）。
4. 专有名词优先正确写法：`FDE`、`OPC`、流程革命、洞察革命等（以审阅稿为准）。
5. 改完后写回对应路径（竖屏 / 横屏各一份），再 `pack`；不要另存破坏路径约定。

## 输入

- 草稿：`temp/<theme>/highlight_竖屏.srt`、`temp/<theme>/highlight_横屏.srt`
- 对照（可选）：`temp/<theme>/review_script.md` 口播摘录

## 输出

完整 SRT 文件内容（或说明「无需修改」）。若修改：只动各 cue 的文本行。

## 与主链关系

见 [`docs/workflows/dualcam-auto-highlight.md`](../../../docs/workflows/dualcam-auto-highlight.md)：映射保证声画轴对齐；本步只抬可读性，不重跑 ASR。
