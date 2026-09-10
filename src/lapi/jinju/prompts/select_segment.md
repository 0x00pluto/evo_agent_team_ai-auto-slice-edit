# 单条金句评分（粘贴词表后输出 JSON）

## 输入

- 主题：`{{theme}}`
- 候选窗口词表（`dump_words_window.py` 输出）
- 是否已在主 timeline：`{{in_main_timeline}}`（是则需更强理由才 keep）

## 评分

语义（可独立上屏、一句收束、跟峰会主题相关）+ 听感（`falling` | `punchy`）。  
任一不合格 → `action: drop`。

## 输出（只输出 JSON）

```json
{
  "action": "keep",
  "start": 0.0,
  "end": 0.0,
  "shot": "closeup",
  "quote": "口播全文（贴词界后）",
  "delivery": "punchy",
  "reason": "一句话：为何可作压轴 + 听感依据"
}
```

或：

```json
{
  "action": "drop",
  "reason": "半截 / 疑问收尾 / 与主片结尾重复 / …"
}
```

约束：

- `start`/`end` 必须落在词边界上；禁止半截。
- 默认 `shot: closeup`（金句特写）。
- `delivery` 仅 `falling` | `punchy`。
- 单条建议 5～14s；过长先砍铺垫再 keep。
