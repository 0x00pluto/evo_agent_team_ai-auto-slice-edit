### **Q: 为什么 ElevenLabs STT 报 401，能不能改用 Whisper 回退？**

**A:**
`call_elevenlabs_stt` 抛出 `HTTPError: 401 Unauthorized` 时，根因是 `$ELEVENLABS_API_KEY` **无效、吊销或缺少 STT 所需权限**，不是「该换引擎」。**禁止**用本机 `mlx_whisper` / OpenAI Whisper 等本地回退顶替；修好密钥后只走 ElevenLabs + MD5 cache。

**问题症状：**
- `scripts/transcribe_video.py` 抽完临时音频后失败，栈在 `src/lapi/stt.py` → `resp.raise_for_status()`
- 环境里 key **有值**仍 401
- 对 `GET https://api.elevenlabs.io/v1/user` 探测可能返回 `authentication_error` / `missing_permissions`

**根本原因：**
- 401 = 密钥不合格或权限不足；**不是**「没装 Whisper / 该回退」的信号
- 额度不足（402 等）同样停工换 key 或问用户，**不**改本地转写

**解决方案：**
1. 在 ElevenLabs 控制台换一把带 Speech-to-Text（scribe）权限的有效 API key，更新 shell 环境后重开终端。
2. 先用极短音频或 `scripts/transcribe_video.py` 验证；成功后 md5 进 `cache/transcripts/`，登记 `sources.json.stt`。
3. 密钥未修好 → **停下来问用户**，不要擅自换引擎。

**错误配置示例：**
```bash
# ❌ 401 / 额度不足时改本机 Whisper「先把活干完」
.venv/bin/python -c "import mlx_whisper; mlx_whisper.transcribe(...)"
# 或手写本地转写假充 ElevenLabs cache
```

**正确配置示例：**
```bash
# ✅ 只走本仓 ElevenLabs 入口；命中 cache 则不打 API
.venv/bin/python scripts/transcribe_video.py \
  "/path/to/wide.mp4" --theme 某访谈枢纽

# 密钥探测（勿把完整 key 贴进对话/提交）
echo "key_len=${#ELEVENLABS_API_KEY}"
curl -sS -H "xi-api-key: $ELEVENLABS_API_KEY" \
  "https://api.elevenlabs.io/v1/user" | head -c 400
```

**关键配置要点：**
- **唯一正式 STT**：ElevenLabs `scribe_v1`（[`src/lapi/stt.py`](../../src/lapi/stt.py) / [`scripts/transcribe_video.py`](../../scripts/transcribe_video.py)）
- **禁止回退**：`mlx_whisper`、`whisper`、其它云 STT；401 / 402 / 额度不足 → 停工，换 key 或等人确认，**不**写本地转写冒充 cache
- 开剪前仍按 MD5 查 `cache/transcripts/`；命中禁止重跑

**参考文档：**
- [`docs/faqs/访谈粗剪-分段异源与叙事选句.md`](./访谈粗剪-分段异源与叙事选句.md)（STT 查 cache 顺序）
- 环境变量：`AGENTS.md` → `$ELEVENLABS_API_KEY`
