# 记忆巩固与遗忘

仓级记忆卫生手册。审视本仓「长期记忆面」（AGENTS / workflows / faqs / 索引）与近轮增量，通过**冲突消解 → 情景提纯 → 剪枝遗忘**，去掉过期住址，留下可迁移规则与负面约束。

**仅**在用户明确要求「遗忘 / 记忆巩固 / consolidate-memory / 剪枝记忆」时触发。**禁止**在任务结束后自行启动；**禁止**定时夜跑。不要在聊天里另起一套散文而不改文件。

与兄弟流分工（手动触发、互不串联）：

| 流 | 管什么 |
|---|---|
| [`post-task-reflect.md`](./post-task-reflect.md) | 本轮**步骤**该不该存在（删 → 程序化） |
| [`extract-experience.md`](./extract-experience.md) | 抽到**项目无关**最佳实践 |
| **本篇** | 本仓常驻人格里的冲突、过期事实、场次专名剪枝 |

## 入口

打开本文件，按「日常步骤」改仓。入口不是 CLI。不做向量库、不做平行 `.agent_memory/` JSON 真相源。

## 参数

| 参数 | 说明 |
|---|---|
| 长期记忆面 | 默认：`AGENTS.md`、`docs/workflows/`、`docs/faqs/`、`docs/doc_index.md` |
| 增量范围 | 近轮改过的 docs / FAQ / 对话里新立的场次专名、禁窗、别字表；可选 `git diff` |
| 是否动导演提示词 | 默认**否**（只读标冲突）；用户点名改口味才动 `src/lapi/director/prompts/` |

## 日常步骤

顺序不可颠倒：

```text
读记忆面 + 增量
→ 1 冲突与时效检测
→ 2 提纯与合并（情景 → 规则）
→ 3 剪枝落盘
→ 回复 refactoring_summary
```

### 0. 输入

- **Existing**：上述长期记忆面；导演提示词默认只读。
- **Recent**：本轮 / 近几轮新增的场次住址、事故现场、互殴表述。

### 1. 冲突与时效检测（Detect）

对每条候选记忆问：

1. 是否与更新的约定矛盾？（例：机位随片源 vs「第三机不做」）
2. 是否已失效的环境快照？（密钥前缀、zshrc 布局、临时任务状态、已修死循环）
3. 是否无跨场指导意义？（手法占位名、人名路径别名、幽灵脚本路径、某场禁窗/ASR 表写进仓级 FAQ）

标出：冲突项 / 失效项 / 衰减淘汰项。**尚未落盘。**

### 2. 提纯与合并（Consolidate）

- **情景 → 语义**：删掉故事，留下定律（`401 + 某 key` → 「401=换 key；禁止 Whisper」）。
- **试错 → SOP**：成功路径写入/改短 `docs/faqs/` 或 `docs/workflows/` 检查清单。
- **归类落点**（代替平行记忆库）：

| 类别 | 落哪里 |
|---|---|
| Semantic | AGENTS 环境/目录约定；workflow 参数事实 |
| Procedural | workflows 日常步骤；FAQ 跨场规则 |
| Active Constraints | 「禁止…」节；负面知识（**优先于**普通事实） |

宁缺毋滥：不确定的临时猜测**不进**长期记忆。

### 3. 剪枝落盘（Prune）

- 物理删除过期住址；提纯后的规则留下。
- 有变更才改文件；同步 [`docs/doc_index.md`](../doc_index.md) 摘要。
- 回复给出 `refactoring_summary`（见下）；**不**另存 `updated_memory.json` 当唯一真相——真相在改完的 Markdown。

### 绝不可删（硬约束）

- **Active Constraints / 负面知识**（例：禁止 Whisper 回退、禁止假 cache、访谈勿套峰会 `plan`）——曾经踩过的坑优先级最高，剪枝时严禁漏删后反写成「可以回退」
- 可迁移定律：分段 STT + md5 溯源、枢纽不打戳 / 成片区打戳、人耳排回音、升序 cut 契约、cleanup 永不删 cache/sources
- 程序化闸门与入口脚本（例：`check_interview_timeline.py`、`cleanup_temp_media.py`）
- 峰会导演词里的产品口味（如 FDE/OPC）：**默认不删**；仅用户明确要求改口味再动

### 重构协议（精简 Dreaming）

角色：离线整理与遗忘引擎。法则：

1. **Detect & Forget**：新旧冲突删旧留新；失效上下文删掉；一次性废话衰减淘汰。
2. **Consolidate & Generalize**：情景→语义；试错→可复用 SOP。
3. **De-duplication**：合并语义重复；负面约束不得被「去重」冲掉。

回复摘要 schema（对话内即可，勿单独建库文件）：

```json
{
  "refactoring_summary": {
    "forgotten_entries": ["删除了废弃信息：[原因及原条目]"],
    "consolidated_skills": ["提纯的通用规则：[描述]"],
    "resolved_conflicts": ["[旧条目] -> [新条目]"]
  }
}
```

## 产物

- 更新后的 `AGENTS.md` / `docs/workflows/` / `docs/faqs/` / `docs/doc_index.md`（若有变更）
- 对话内 `refactoring_summary`
- **不是**反思散文、不是跨项目 `docs/best-practices/`（那走 extract-experience）
- 仓无文件变更且明确「无可剪」→ 合法结束

## 失败排查

| 现象 | 处理 |
|---|---|
| 只写了摘要，仓没变 | 有该删/该提纯则必须改文件；否则写「无可剪」并停 |
| 任务结束后自动跑了本流 | 停；仅用户明确要求时触发 |
| 删掉了「禁止 Whisper」类负面约束 | 立刻恢复；重跑 Stage 2/3，负面优先 |
| 把场次禁窗/ASR 表写进仓级 FAQ | 移回本场 `sources.md` / prompt；FAQ 只留跨场定律 |
| 改了导演提示词口味但用户未点名 | 回滚；默认只读标冲突 |
| 与 post-task-reflect / extract-experience 串成一套 | 停；三流互不串联 |
| 在本流里再次触发本流 | 套娃；直接结束 |
| 新建 `.agent_memory/` 或向量库 | 禁止；本仓只用版本化 Markdown |

## 测试

人工验收至少满足：

- 仓级 docs 更短或冲突表述减少
- `refactoring_summary` 中 forgotten / resolved 与 diff 对应
- 负面约束与可迁移定律仍在索引可达路径上
