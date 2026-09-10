# 单段镜头导演模板（每次只处理一段）

把下面占位符换成真实内容；**一次只改一段**（或明确要拆开的本段）。  
机位只能是 `closeup` | `wide`。

---

## 输入

**主题**：{{theme}}

**本段编号**：#{{index}}

**当前区间**：{{start}} → {{end}}（秒）  
**当前 shot**：{{shot}}  
**当前摘录**：

```
{{excerpt}}
```

**下一段开头预览**（判断要不要在本段尾换气；无则写「无」）：

```
{{next_excerpt}}
```

**词级时间码**（可选；要拆段时必填，`dump_words_window.py` 输出）：

```
{{words_table}}
```

---

## 任务

依据 [`shot_director.md`](./shot_director.md)：

1. 整段一种机位是否够用？够 → `keep` 或只改 `shot`。
2. 需要定场/换气 → 仅在停顿处拆成多段，各赋 `closeup` 或 `wide`。
3. 不要为镜头改语义边界（叠词挖空等已由语义快剪定好）。

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
      "reason": "原 reason + 镜头:… "
    }
  ],
  "notes": "给人看的备注"
}
```

`action`：

- `replace`：用 `segments` 替换本段（1 条或多条连续）
- `keep`：本段机位与边界都不用改，`segments` 可空

时间必须落在词边界或原段起止上。
