# 金句筛选（京剧口语 = 金句）

> 本篇是峰会手法 [`summit-highlight`](./summit-highlight.md) 的**金句子步骤**；机位随 `sources`；开剪总入口见 [`choose-edit-style`](./choose-edit-style.md)。

峰会叙事初剪之后的**交付必做闸门**：挑 2～3 条可单独上屏的压轴金句（听感：降调落地 / 铿锵有力），按 `sources` **有几轴出几轴**切备选条，并把**推荐金句焊进成片末尾**（双机实践为特写 / 全景 / 混剪三条）。最终不另出第四条「含推荐收尾」。模块与主 `timeline.json` 文件隔离，可单独迭代提示词。

## 入口

在仓根执行：

```bash
.venv/bin/python scripts/run_jinju.py --help
```

前置：同主题成片工作区（`--theme` 短名 → resolve 最新戳；或写带戳全名）已有 `transcript.json` + `sources.json`，且主链已 `cut` 出**叙事成片**（轴数随 `sources`；双机实践为特写/全景/混剪三片，会快照到 `narrative/`）。

导演提示词（热调，只动本模块）：

- [`src/lapi/jinju/prompts/select.md`](../../src/lapi/jinju/prompts/select.md)
- [`src/lapi/jinju/prompts/select_segment.md`](../../src/lapi/jinju/prompts/select_segment.md)

## 参数

| 命令 / 参数 | 说明 |
|---|---|
| `nominate --theme` | 写 `temp/<theme>/jinju/candidates.json` 草稿 |
| `nominate --force` | 覆盖已有草稿 |
| `nominate --from-json` | 从外部 JSON 导入并校验 |
| `export --theme` | 按 sources 轴数裁切同时间码金句条 + `review.md` |
| `export --closeup` / `--wide` | 覆盖对应轴路径 |
| `pack --theme` | `jinju/` 备选 + **焊尾进叙事成片**（轴数随 sources；双机实践为三条）+ 更新横竖屏字幕末 cue |

机位解析：读 `sources.json` 的 `closeup` / `wide`，或嵌套 `axes: {…}`。有几轴出几轴。

焊尾规则（双机实践）：

- 特写高光 = 叙事特写 + 推荐**特写**条
- 全景高光 = 叙事全景 + 推荐**全景**条
- 混剪高光 = 叙事混剪 + 推荐**特写**条（音轨同特写）

## 日常步骤

1. 读 [`select.md`](../../src/lapi/jinju/prompts/select.md)；对照主 `timeline.json` 避重。
2. `dump_words_window.py` 贴词界；套 [`select_segment.md`](../../src/lapi/jinju/prompts/select_segment.md)。
3. 写入 `candidates.json`（`recommended` = 推荐下标）。
4. 人确认推荐压轴。
5. `export` → `pack`。
6. 听各轴成片末尾（双机实践为三条）；要换结尾：改 `recommended` 或告诉剪辑用 `jinju/` 对应轴条替换最后一截，再 `pack`。

## 产物

### temp 工作区（勿上传）

| 路径 | 用途 |
|---|---|
| `temp/<theme>/jinju/candidates.json` | 候选 / recommended |
| `temp/<theme>/jinju/axes.txt` | 轴清单 |
| `temp/<theme>/narrative/*_高光.mp4` | 叙事底片（可重入焊尾，防叠尾） |
| `temp/<theme>/jinju/*.mp4` | 导出中间件 |

### output 剪辑包（上传）

| 路径 | 用途 |
|---|---|
| `output/<theme>/<theme>_特写/全景/混剪_高光.mp4` | **最终成片（末尾已含推荐金句；双机实践为三条）** |
| `output/<theme>/review_script.md` / `highlight_竖屏.srt` / `highlight_横屏.srt` | 审阅 + 成片轴字幕（含末尾金句 cue） |
| `output/<theme>/jinju/0N_*_特写/全景.mp4` | 备选金句条（换结尾换最后一截） |
| `output/<theme>/jinju/review.md` | 金句听选表 |

**不进 output**：`candidates.json`、`axes.txt`、`timeline.json`、任何 `*含推荐收尾*`。

## 失败排查

| 现象 | 处理 |
|---|---|
| 缺 narrative 底片 | 先 dualcam `cut`，或确认 output 仍有叙事三片再 pack |
| 二次 pack 叠了两段金句 | 删 `temp/<theme>/narrative/` 后从**未焊尾**三片重拷，或重跑 dualcam `cut` |
| 只有特写没有全景条 | 检查 `sources.wide` |
| 仍看到含推荐收尾 | 旧包；重跑 `pack`（会删除） |

## 测试

```bash
.venv/bin/python -m unittest discover -s tests/src/lapi -p 'test_jinju*.py' -v
```
