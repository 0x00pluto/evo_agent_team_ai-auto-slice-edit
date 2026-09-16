# 峰会高光（剪辑手法总览）

把峰会长片收成对外宣传初剪：叙事通顺、目标约 60–120s，再焊一条可上屏金句收尾，并交付多轴金句备选。本篇**编排**子步骤，细节见链接；不重写 CLI。

> 子步骤：[`dualcam-auto-highlight.md`](./dualcam-auto-highlight.md)（叙事）→ [`jinju-select.md`](./jinju-select.md)（金句）。开剪前先经 [`choose-edit-style.md`](./choose-edit-style.md) 选型。

## 入口

无独立 CLI。选型确认「峰会高光」后读本篇，再下钻子步骤。

实现入口名暂为 `dualcam`（历史文件名），**手法不绑死双机**。

在仓根执行：

```bash
.venv/bin/python scripts/run_dualcam_lapi.py --help
.venv/bin/python scripts/run_jinju.py --help
```

## 机位（随片源）

**机位数 = 用户本场提供的有效片源路数**（常见 1 / 2 / 3；更多按 `sources` 登记）。选型时不问双机还是三机；按用户文件与角色写入成片工作区 `sources.json`（或 `sources.axes`）。

| 路数 | 交付约定 |
|---|---|
| 单机 | 只出该轴成片 + 同轴金句备选；不做假混剪机位 |
| 双机（特写+全景） | 现有实践：特写 / 全景 / 混剪三片 + 金句双轴 |
| 三机及以上 | 叙事与金句均**有几路出几路**；镜头导演只在已有轴标签间切换 |

缺音源路时默认用特写；仅单机则该路兼任音源。**不臆造用户未提供的机位。**

已知缺口：`run_dualcam_lapi.py` 当前 CLI 仍偏双机假设（`--wide` / `--closeup`）。单机 / 三机以文档约定为准；程序化补齐留后轮，本轮不改 `src/`。

## 参数

| 参数 | 说明 |
|---|---|
| 片源路径 | 用户提供的 1～N 路同步长片 |
| `--theme` | 主题**短名** → plan 新建 `temp/<短名>_YYYY_MM_DD_HH_MM/`；cut/jinju 可用短名 resolve；`output/<短名>/` **不打戳** |
| `--target-seconds` | 叙事目标时长，峰会宣传常见 65 左右（容差随场次） |

导演提示词仍在子步骤模块内热调，本篇不重复。

## 日常步骤

### 路径 A：从零完整剪（主片 + 金句）

1. 登记 `sources`：用户给几路写几路（`closeup` / `wide` / 其他轴名）。
2. 跑 [`dualcam-auto-highlight.md`](./dualcam-auto-highlight.md)：`plan` → 语义快剪 → 镜头导演 → 人确认 → `cut`（叙事底片 + 横竖屏字幕草稿）。
3. 跑 [`jinju-select.md`](./jinju-select.md)：nominate → 人确认推荐 → `export` → `pack`（焊尾 + `jinju/` 备选 + 字幕末 cue）。
4. 交付初检通过后 → [`cleanup-temp-media.md`](./cleanup-temp-media.md)（dry-run → `--apply`）。

### 路径 B：主片已定，只补金句

主 `timeline` 不动（叙事已定、只焊金句收尾）：

1. 确认成片工作区（短名 resolve 到最新戳）有 `transcript.json`、`sources.json`，且叙事成片在 `output/` 或可快照到 `narrative/`。
2. 只跑 [`jinju-select.md`](./jinju-select.md)。
3. 交付初检通过后 → [`cleanup-temp-media.md`](./cleanup-temp-media.md)。

## 产物

只传 `output/<theme>/`：

- 成片（轴数随 sources；双机实践为特写 / 全景 / 混剪，末尾已含推荐金句）
- `review_script.md`
- `highlight_竖屏.srt` / `highlight_横屏.srt`
- `jinju/`：2～3 条 × 同时间码多轴 + `review.md`

**不进 output**：`timeline.json`、`candidates.json`、第四条「含推荐收尾」。

## 失败排查

| 现象 | 处理 |
|---|---|
| 未选型就开剪 | 回 [`choose-edit-style.md`](./choose-edit-style.md) |
| 只有一路却想出混剪三片 | 单机不做假混剪；只交该轴 |
| 金句只有特写没有全景 | 检查 `sources.wide`；有几轴出几轴 |
| 二次 pack 叠了两段金句 | 见 jinju 排查：从 narrative 未焊尾底片重来 |
| CLI 强制要 wide+closeup | 当前实现缺口；单机场次先登记 sources 并人工对齐交付轴，或暂用「不用模板」探索 |

## 明确不做

访谈口播剪、推拉摇、精剪调色、成片发布；不对高光成片重新 STT。

## 测试

子步骤单测：

```bash
.venv/bin/python -m unittest discover -s tests/src/lapi -v
```
