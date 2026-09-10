"""ElevenLabs STT：ffmpeg 抽音频 → scribe_v1 逐词时间戳 → MD5 缓存。"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Callable

import requests

STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"
DEFAULT_TIMEOUT = 900


def file_md5(path: str | Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def cache_path(cache_dir: Path, md5: str) -> Path:
    return cache_dir / f"{md5}.json"


def load_cache(cache_dir: Path, md5: str) -> dict[str, Any] | None:
    path = cache_path(cache_dir, md5)
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "text" not in data:
            return None
        return data
    except (json.JSONDecodeError, OSError):
        return None


def save_cache(cache_dir: Path, md5: str, data: dict[str, Any]) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_path(cache_dir, md5)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def extract_audio(
    video_path: str | Path,
    audio_path: str | Path,
    *,
    run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> None:
    audio_path = Path(audio_path)
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-acodec",
            "libmp3lame",
            "-ar",
            "16000",
            "-ac",
            "1",
            "-b:a",
            "48k",
            str(audio_path),
        ],
        check=True,
        capture_output=True,
    )


def call_elevenlabs_stt(
    audio_path: str | Path,
    api_key: str,
    *,
    timeout: int = DEFAULT_TIMEOUT,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    http = session or requests
    with open(audio_path, "rb") as f:
        resp = http.post(
            STT_URL,
            headers={"xi-api-key": api_key},
            files={"file": f},
            data={
                "model_id": "scribe_v1",
                "timestamps_granularity": "word",
            },
            timeout=timeout,
        )
    resp.raise_for_status()
    return resp.json()


def words_to_srt(words: list[dict[str, Any]], max_chars: int = 32) -> str:
    """把逐词时间戳粗拼成 SRT（按字符数切 cue）。"""
    cues: list[tuple[float, float, str]] = []
    buf: list[str] = []
    start: float | None = None
    end: float = 0.0

    def flush() -> None:
        nonlocal buf, start
        if not buf or start is None:
            return
        cues.append((start, end, "".join(buf).strip()))
        buf = []
        start = None

    for w in words:
        text = str(w.get("text") or "")
        if not text.strip():
            continue
        w_start = float(w["start"])
        w_end = float(w["end"])
        if start is None:
            start = w_start
        buf.append(text)
        end = w_end
        if len("".join(buf)) >= max_chars or text.endswith(("。", "！", "？", ".", "!", "?")):
            flush()
    flush()

    lines: list[str] = []
    for i, (s, e, text) in enumerate(cues, start=1):
        lines.append(str(i))
        lines.append(f"{_ts(s)} --> {_ts(e)}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


def _ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3600_000)
    m, rem = divmod(rem, 60_000)
    s, milli = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{milli:03d}"


def transcribe_video(
    video_path: str | Path,
    *,
    cache_dir: Path,
    temp_dir: Path,
    api_key: str | None = None,
    force: bool = False,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[dict[str, Any], str, bool]:
    """
    返回 (result, md5, from_cache)。
    from_cache=True 表示未打 API。
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"视频不存在: {video_path}")

    key = api_key if api_key is not None else os.environ.get("ELEVENLABS_API_KEY")
    md5 = file_md5(video_path)

    if not force:
        cached = load_cache(cache_dir, md5)
        if cached is not None:
            return cached, md5, True

    if not key:
        raise RuntimeError("请设置 ELEVENLABS_API_KEY 环境变量")

    temp_dir.mkdir(parents=True, exist_ok=True)
    audio_path = temp_dir / f"audio.{md5}.mp3"
    extract_audio(video_path, audio_path)
    result = call_elevenlabs_stt(audio_path, key, timeout=timeout)
    save_cache(cache_dir, md5, result)
    return result, md5, False
