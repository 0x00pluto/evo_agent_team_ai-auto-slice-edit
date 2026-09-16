# 清理 temp 可重建大媒体

交付初检通过后，删掉 `temp/` 里「大、重建便宜」的媒体，保留续剪命根（转写 / sources / timeline）。避免每场剪完 temp 越垒越大。

本篇是业务可复跑动作；实现入口：[`scripts/cleanup_temp_media.py`](../../scripts/cleanup_temp_media.py)。

## 入口

在仓根执行：

```bash
.venv/bin/python scripts/cleanup_temp_media.py --help
```

触发：`output/<交付名>/` 齐套且本轮 cut/pack 完成（人可听混剪）之后 **必须** 跑本流；不另等用户说「清一下」。

## 参数

| 参数 | 说明 |
|---|---|
| （默认） | dry-run：只打印可删目标与合计体积，不删 |
| `--apply` | 真正删除 |
| `--theme <名>` | 只扫 `temp/<theme>/`；**须精确目录名**（成片区含时间戳时写全名，如 `{短名}_{YYYY_MM_DD_HH_MM}`）；不做短名解析；省略则扫全部 `temp/*` |
| `--orphan-parts` / `--no-orphan-parts` | 默认开：父主题已有合并 `transcript.json` 时，删 `temp/<theme>_partN/` |

## 规则

### 永不删

- `cache/transcripts/`（整仓）
- `sources.md` / `sources.json`（含 stt 溯源）
- `transcript.json` / `transcript.srt`
- `timeline.json` / `review_script.md` / `highlight_*.srt`
- `*_concat.txt` / `concat_list.txt`
- `cut_*.py` 等 temp 内一次性脚本
- `jinju/axes.txt`、`candidates.json`、`review.md`、`jinju/transcript.*`
- **禁止**删 `output/`、任意转写 / sources / timeline

### 交付初检后可删（大、重建便宜）

| 目标 | 重建方式 |
|---|---|
| `aligned/*.mp4`、`source_concat.mp4` | `ffmpeg -f concat -c copy` + `*_concat.txt` |
| `cuts/`、`narrative/` | 再跑 cut / snapshot |
| `jinju/_bake/`、`jinju/_preview/`、`jinju/*.mp4` | 金句 export / pack（交付在 `output/`） |
| `audio.*.mp3` | STT 前再抽 |
| `temp/<theme>_partN/`（父主题已有合并 `transcript.json`） | 不重建；合并稿在父主题 |

## 日常步骤

1. 确认本轮交付包在 `output/` 齐套（或用户已确认混剪可听）。
2. dry-run：

```bash
.venv/bin/python scripts/cleanup_temp_media.py
# 或只清本场（精确目录名）：
.venv/bin/python scripts/cleanup_temp_media.py --theme '{短名}_{YYYY_MM_DD_HH_MM}'
```
3. 核对列表无「永不删」项后 `--apply`：

```bash
.venv/bin/python scripts/cleanup_temp_media.py --apply
# 或
.venv/bin/python scripts/cleanup_temp_media.py --theme <theme> --apply
```

4. 抽查：`sources.md` / `transcript.json` / `timeline.json` / `*_concat.txt` 仍在；`aligned/*.mp4`、`cuts/`、`narrative/`、`jinju/*.mp4` 已无。

同素材多方向（枢纽 aligned 被多条成片共用）：本场交付后可清该成片工作区 `cuts`/`narrative`；父主题枢纽 `aligned/*.mp4` 在不再续剪时一并精确 `--theme` 或全仓 apply（保留 `*_concat.txt`，需要时 stream copy 重拼）。

## 产物

- dry-run / apply 终端清单与合计体积
- `temp/` 体积下降；续剪所需小文件保留

## 失败排查

| 现象 | 处理 |
|---|---|
| dry-run 空 | 已清过，或 theme 名不对 |
| 续剪要 cut 却缺 aligned | 用 `aligned/*_concat.txt` 重拼 mp4；勿重跑 STT |
| 误担心转写被删 | 脚本永不删 transcript / sources / cache |
| part 目录还在 | 确认父主题有 `transcript.json`；或显式 `--orphan-parts` |
| 想清 output | 禁止；本流不管 output |

## 测试

```bash
.venv/bin/python -m unittest tests.scripts.test_cleanup_temp_media -v
```
