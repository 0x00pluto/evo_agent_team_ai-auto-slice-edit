# 双机位自动高光拉片

> 本篇是峰会手法 [`summit-highlight`](./summit-highlight.md) 的**叙事子步骤**；机位随 `sources`；开剪总入口见 [`choose-edit-style`](./choose-edit-style.md)。CLI 文件名 `dualcam` 为历史名，不表示手法必须双机。

按脚本把 1～N 路同步长片收成**语句通顺的高光初剪**，打包交后期精剪。主链：规则粗筛 → Agent 语义快剪 → **镜头导演（特写/全景等已有轴）** → 人确认 → 交付（含与成片轴严格对齐的 `highlight_竖屏.srt` / `highlight_横屏.srt`）。不做剪映精剪、调色与成片发布。

> 复盘口径：主链含交付目录分层与 A/B 镜头导演；**跳过程序化与鲁棒**。推拉摇/成片运镜不在本仓本轮。高光轴字幕由 transcript 映射生成，可选 Agent 纠错别字。

## 入口

```bash
cd /Users/peng.zhi/Documents/Codex/AI自动化切片剪辑拉片
uv pip install -r requirements.txt   # 首次
.venv/bin/python scripts/run_dualcam_lapi.py --help
```

## 目录分层

| 目录 | 用途 | 上传？ |
|---|---|---|
| `temp/<theme>_<YYYY_MM_DD_HH_MM>/` | 成片工作区（plan 新建时自动打东八区戳；cut 可用短名 resolve 到最新戳） | **否** |
| `output/<theme>/` | **干净交付包**：三片（末尾含推荐金句）+ 审阅 + 横竖屏字幕 + `jinju/` 备选；**不打戳** | **是（只传这一层）** |
| `cache/transcripts/` | STT MD5 缓存 | 否 |

实现：[`src/lapi/theme_dir.py`](../../src/lapi/theme_dir.py)（`allocate_temp_dir` / `resolve_temp_dir`）。

## 参数

| 参数 | 说明 |
|---|---|
| `plan --wide` | 全景视频路径 |
| `plan --closeup` | 特写视频路径（STT / 音源默认这一路） |
| `plan --theme` | 主题**短名** → 新建 `temp/<短名>_YYYY_MM_DD_HH_MM/`；`output/` 仍用短名 |
| `plan --target-seconds` | 高光总时长，默认 120 |
| `plan --force-stt` | 忽略 MD5 缓存强制重转写 |
| `plan --yes-cut` | 无人值守跳过闸门（日常勿用；会跳过语义快剪） |
| `cut --theme` | 短名或带戳全名；resolve 到 temp 后出片，组装 `output/<短名>/` |
| `cut --timeline` | 默认 `temp/<resolved>/timeline.json` |
| `cut --wide/--closeup` | 可覆盖 `temp/<resolved>/sources.json` |
| `pack --theme` | 不重裁；缺横竖屏字幕时从 transcript+timeline 生成草稿后组装 |

导演提示词（热调）：[`src/lapi/director/prompts/`](../../src/lapi/director/prompts/)

- 规则粗筛：`system.md` / `selection.md` / `shots.md` / `fillers.md`（预处理，**不是**可交片终态）
- **语义快剪（Agent 对话，不嵌模型 HTTP API）**：[`semantic_polish.md`](../../src/lapi/director/prompts/semantic_polish.md) + [`semantic_polish_segment.md`](../../src/lapi/director/prompts/semantic_polish_segment.md)
- **镜头导演（仅 `closeup`|`wide`）**：[`shot_director.md`](../../src/lapi/director/prompts/shot_director.md) + [`shot_director_segment.md`](../../src/lapi/director/prompts/shot_director_segment.md)
- **高光字幕纠错**：[`highlight_srt_polish.md`](../../src/lapi/director/prompts/highlight_srt_polish.md)（只改正文别字，**禁止改时间码**）

## 主链（日常步骤）

目标一句话：**按脚本意图剪到目标时长附近，语句通顺，特写/全景有切换，交付齐套（含成片轴 SRT）。**

### 0. 职责边界（删透镜结论）

| 步骤 | 去留 |
|---|---|
| 音源路 STT + 缓存 | 留（词级时间码） |
| 规则 plan 粗筛（主题/时长） | 留；允许仍有叠词/半截；产物在 `temp/` |
| 规则 fillers / 半截修补 / 碎切当终态 | **降级**为预处理；听感终态 = 语义快剪后的 timeline |
| Agent 逐段语义快剪 | 留（语句通的关键） |
| Agent 镜头导演（特写/全景） | **留**；终态混剪靠本步 |
| 刷新审阅 + 人确认再 cut | 留；cut 映射横竖屏字幕并组装干净 `output/` |
| 高光字幕：transcript 按 timeline 映射成片轴（竖≤14 / 横≤20） | **留**；与成片时间严格对齐（`t' = t - seg.start + cursor`） |
| Agent 字幕别字纠错 | **留**（对话闸门）；不重跑 ASR；不改 cue 时间 |
| 对成片重新 STT | **不做**（易错位） |
| 推拉摇 / 缩放 / 第三机 | **不做**（成片精剪阶段） |
| 代码内调外部 LLM API | 禁止；判断在 Agent 对话里做 |

### 1. 原料

- 1～3 路**同时长**同步片（当前实践：全景 + 特写）。
- 主题 / 脚本意图、目标时长（如 120s）。

### 2. plan（规则粗筛）

特写 STT → 规则导演 → 粗 `temp/<theme>/timeline.json` + `review_script.md`，进程结束。  
产出只要求「够主题、够时长量级」；**不要**在此步追求听感终态。

### 3. 语义快剪闸门（Agent）

在 Agent 对话中做（不嵌仓库内模型 API）：

1. 读 [`semantic_polish.md`](../../src/lapi/director/prompts/semantic_polish.md)
2. 对审阅稿**每一段**（可合并相邻半截段）：
   ```bash
   .venv/bin/python scripts/dump_words_window.py --theme <主题> --start <s> --end <e>
   ```
   词表贴进 [`semantic_polish_segment.md`](../../src/lapi/director/prompts/semantic_polish_segment.md)，按输出 JSON 改 **`temp/<theme>/timeline.json`**
3. 全部改完后刷新审阅（可与镜头导演后合并刷新一次）。

原则：叠词只留末次；禁止半截收尾；相邻段拼接能听顺；少切；跟脚本主题。

### 4. 镜头导演闸门（Agent，仅 A/B）

语义听感 OK 后，再挂机位（**只改 `shot`，或在停顿处拆段换机位**）：

1. 读 [`shot_director.md`](../../src/lapi/director/prompts/shot_director.md)
2. 逐段套 [`shot_director_segment.md`](../../src/lapi/director/prompts/shot_director_segment.md)；需要拆段时用 `dump_words_window.py` 找停顿
3. 写回 `temp/<theme>/timeline.json`
4. 刷新审阅：
   ```bash
   .venv/bin/python scripts/refresh_review.py --theme <主题>
   ```

原则：主特写、辅全景；金句/主题词偏特写；定场/换气/列举过渡可用全景；禁句中硬切；单镜建议 ≥ 2.5s。

### 5. 人确认 → 交付

听审阅摘录与**混剪**听感（应能感到特写/全景切换）；确认后 `cut`：

1. ffmpeg 出三片（同时间轴）
2. 从 `transcript.json` + `timeline.json` **映射** `temp/<theme>/highlight_竖屏.srt` + `highlight_横屏.srt`（成片轴从 0 起；断句符→空格；竖≤14 / 横≤20 字）
3. （推荐）读 [`highlight_srt_polish.md`](../../src/lapi/director/prompts/highlight_srt_polish.md) 只改正文别字，**不动时间码**（横竖屏各改各的，或先改竖屏再确认横屏）
4. `pack` 写入 `output/<theme>/`（上传只传这一目录；**不含** `timeline.json`）
5. 交付初检通过后 → [`cleanup-temp-media.md`](./cleanup-temp-media.md)（先 dry-run 再 `--apply`；勿跳过）

```bash
.venv/bin/python scripts/run_dualcam_lapi.py plan \
  --wide "/path/全景.mp4" \
  --closeup "/path/特写.mp4" \
  --theme 李桢峰会 \
  --target-seconds 120

# … Agent 语义快剪 → 镜头导演，改 temp/<theme>/timeline.json …
.venv/bin/python scripts/refresh_review.py --theme 李桢峰会

.venv/bin/python scripts/run_dualcam_lapi.py cut --theme 李桢峰会
# … 可选：Agent 纠错 temp/<theme>/highlight_竖屏.srt / highlight_横屏.srt …
.venv/bin/python scripts/run_dualcam_lapi.py pack --theme 李桢峰会
```

### 流程级验收

- 总长贴近目标；与脚本主题相关
- 无刺耳叠词、无「开始慢｜慢慢地」类半截断裂
- 多路成片共用同一时间轴
- **混剪**可见特写/全景切换（非全程特写）
- **横竖屏字幕与成片声画轴对齐**（导入剪映后 scrub 对词无漂移；无 `highlight.srt` 别名）
- **`output/<theme>/` 交付清单齐套**：三片（已焊推荐金句）+ `review_script.md` + `highlight_竖屏.srt` + `highlight_横屏.srt` + `jinju/`（多轴备选 + `review.md`）；无 transcript/sources/`timeline.json`/`candidates.json`/`axes.txt`/第四条「含推荐收尾」

## 交付清单

给剪辑人员的一包（**仅** `output/<theme>/`；视频负责看/听；文稿/字幕负责对着剪与导入剪映）：

| 交付物 | 用途 | 状态 |
|---|---|---|
| `<theme>_特写_高光.mp4` | 精剪底；**末尾已含推荐金句（特写轴）** | **交付必带** |
| `<theme>_全景_高光.mp4` | 同轴画面；**末尾已含推荐金句（全景轴）** | **交付必带**（有全景源时） |
| `<theme>_混剪_高光.mp4` | 推荐初看；**末尾已含推荐金句（特写轴接）** | **交付必带** |
| `review_script.md` | 口播/脚本对照表（时间码 + 摘录 + reason/shot） | **交付必带** |
| `highlight_竖屏.srt` | 竖屏剪映导入；≤14 字/cue；与成片轴对齐（含末尾金句） | **交付必带** |
| `highlight_横屏.srt` | 横屏剪映导入；≤20 字/cue；同轴 | **交付必带** |
| `jinju/` 多轴 `0N_*_特写/全景.mp4` | 备选金句；换结尾时替换成片最后一截 | **交付必带** |
| `jinju/review.md` | 金句听选表（口播 + 推荐下标） | **交付必带** |

工作区（勿上传）：`temp/<theme>/timeline.json`、`transcript.json`、`sources.json`、草稿横竖屏字幕；`temp/<theme>/narrative/`（叙事底片）；`temp/<theme>/jinju/candidates.json`、`axes.txt`；以及 `cache/transcripts/<md5>.json`。

## 金句闸门（交付必做）

叙事 `cut` 后**必须**跑 [`jinju-select.md`](./jinju-select.md)（nominate → 人确认 → export → pack）。  
`pack` 把推荐金句焊进三条成片末尾，并交付 `jinju/` 备选条。一次交付 = **三条成片 + 备选金句**；不另出第四条成片。

## 明确不做（成片阶段）

推拉摇、画面缩放模拟、第三机叠加——不在本仓本轮；精剪工具里再做。  
不对高光成片重新 STT（易与裁切轴错位）；别字只在映射稿上 Agent 纠错。

## 失败排查

| 现象 | 处理 |
|---|---|
| 未设置 ELEVENLABS_API_KEY | 导出环境变量后重跑 plan |
| STT 超时 | 大文件默认 900s；检查网络与音频体积 |
| 导演 segments 为空 | 检查转写 words；放宽 `prompts/selection.md` 最小时长 |
| 半截句 / 叠词 | 走语义快剪闸门，勿只靠规则 fillers |
| 混剪全程特写 | 走镜头导演闸门；检查 `shot` 是否仍全是 closeup |
| cut 找不到源片 | 检查 `temp/<theme>/sources.json` 或显式传 `--wide/--closeup` |
| 声画不同步 | 确认各路源片时长一致；勿对单路单独改时间轴 |
| 字幕与成片对不上 | 确认用的是映射出的 `highlight_竖屏.srt` / `highlight_横屏.srt`（非 `transcript.srt`、非旧 `highlight.srt`）；改 timeline 后须 `cut` 或强制重映射再 pack；纠错时勿改时间码 |
| 交付缺横竖屏字幕 | `pack` 会尝试自动生成；确认 temp 有 `transcript.json` + `timeline.json` |
| output 仍有 timeline.json | 旧包；重跑 `pack` |
| output 里出现 transcript | 旧布局残留；迁到 temp 后 `pack` |

## 测试

```bash
.venv/bin/python -m unittest discover -s tests/src/lapi -v
```
