# 发版说明（upgrades）

面向 GitHub Release 正文，**不是**开发文档（开发文档在 `docs/`）。

每个 Git tag 对应一份 Markdown，文件名与 tag **完全一致**（含 `v` 前缀）。

| tag | 文件 |
|---|---|
| `v0.2.0` | [`v0.2.0.md`](./v0.2.0.md) |
| `v0.1.0` | [`v0.1.0.md`](./v0.1.0.md) |

用 `gh release create` 时把该文件全文作为 Release 正文；**缺少对应文件则禁止建 Release**。

发版前：先写好 `upgrades/vX.Y.Z.md` 并提交，再打 tag 推送。

Agent / 协作流程（查变更 → 写本目录 → 对齐 `evo_agent_pack.json` version → 本地 tag → 推送 / Release）：见 [`docs/builtin-workflows/cut-release-tag.md`](../docs/builtin-workflows/cut-release-tag.md)。版号按 SemVer；**升 major 必须人工显式指定**。

单篇 upgrades **不**登记进 `docs/doc_index.md`。
