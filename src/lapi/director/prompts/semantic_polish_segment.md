# 单段语义快剪模板（每次只处理一段）

把下面占位符换成真实内容，在 Agent 对话中执行；**一次只改一段**（或明确要合并的相邻两段）。

---

## 输入

**主题**：{{theme}}

**本段编号**：#{{index}}

**当前区间**：{{start}} → {{end}}（秒）  
**shot**：{{shot}}  
**当前摘录**：

```
{{excerpt}}
```

**下一段开头预览**（用于判断要不要并段/扩尾；若无则写「无」）：

```
{{next_excerpt}}
```

**词级时间码**（`scripts/dump_words_window.py` 输出，含 index）：

```
{{words_table}}
```

---

## 任务

依据 [`semantic_polish.md`](./semantic_polish.md)：

1. 标出要**挖掉**的口癖/叠词（只留末次「我的」「我觉得」等）。
2. 若尾半截：把 `end` **扩到**语义完整的词（可看下一段预览，必要时并入下一段）。
3. 若头是跨句尾巴：把 `start` **收到**本句开头。
4. 尽量少段：能一条说完的不要拆成听感断裂的两段。

---

## 只输出如下 JSON（不要解释）

```json
{
  "action": "replace",
  "segments": [
    {
      "start": 0.0,
      "end": 0.0,
      "shot": "closeup",
      "reason": "一句话说明改了什么"
    }
  ],
  "notes": "给人看的备注"
}
```

`action` 取值：

- `replace`：用 `segments` 替换本段（可 1 条或多条连续保留片）
- `merge_next`：本段与下一段合并为 `segments` 里的一条（或若干条）
- `keep`：本段无需改，`segments` 可为空

时间必须落在词边界上（用词表里的 start/end）。

全部段处理完后：刷新审阅稿 → 人确认 → 再 `cut` / 交付（见 `docs/workflows/dualcam-auto-highlight.md`）。
