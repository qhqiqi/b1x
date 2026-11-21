# -*- coding: utf-8 -*-
"""LLM 客户端（Anthropic Messages 协议，网关 https://token.b1x.work）。

设计约束来自实测：网关约 1/3 概率 CONNECT_TIMEOUT / ECONNRESET。
  * 3 次指数退避重试
  * 30s 超时
  * 磁盘缓存（演示时命中即秒回，网络挂了也能跑）
  * 无 key 时抛 LLMUnavailable，调用方必须能降级到纯规则

用法：
    from engine.llm import call_llm, json_call, LLMUnavailable
"""
import hashlib
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BS = chr(92)          # 反斜杠
FENCE = chr(96) * 3   # 三反引号


def _load_dotenv() -> None:
    """从项目根 .env 读键值（不覆盖已有环境变量）。"""
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()

BASE_URL = os.environ.get("GTM_HACK_BASE_URL", "https://token.b1x.work").rstrip("/")
MODEL = os.environ.get("GTM_HACK_MODEL", "deepseek-v4.1-flash-1017")
API_KEY = os.environ.get("GTM_HACK_API_KEY", "").strip()
CACHE_DIR = Path(os.environ.get("GTM_HACK_CACHE") or (ROOT / ".cache" / "llm"))
TIMEOUT = 30
RETRIES = 3


class LLMUnavailable(RuntimeError):
    """没有 key / 重试耗尽 —— 调用方应降级到规则引擎。"""


def available() -> bool:
    return bool(API_KEY)


def _cache_path(key: str) -> Path:
    return CACHE_DIR / (hashlib.sha256(key.encode("utf-8")).hexdigest()[:32] + ".json")


def _post(url: str, body: bytes, headers: dict) -> dict:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def call_llm(
    messages: list,
    system: str | None = None,
    max_tokens: int = 2048,
    temperature: float = 0.0,
    use_cache: bool = True,
    verbose: bool = False,
) -> str:
    """返回模型的纯文本输出。失败重试 3 次后抛 LLMUnavailable。"""
    if not API_KEY:
        raise LLMUnavailable("GTM_HACK_API_KEY 未设置（见 .env.example）")

    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages,
    }
    if system:
        payload["system"] = system
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    cpath = _cache_path(raw)

    if use_cache and cpath.exists():
        try:
            hit = json.loads(cpath.read_text(encoding="utf-8"))
            if verbose:
                print("[cache hit] " + cpath.name[:12], file=sys.stderr)
            return hit["text"]
        except Exception:
            pass

    headers = {
        "content-type": "application/json",
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
    }
    url = BASE_URL + "/v1/messages"
    last_err = None
    for attempt in range(RETRIES):
        try:
            data = _post(url, raw.encode("utf-8"), headers)
            text = "".join(
                b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"
            )
            if use_cache:
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                cpath.write_text(
                    json.dumps({"text": text, "usage": data.get("usage", {})}, ensure_ascii=False),
                    encoding="utf-8",
                )
            return text
        except Exception as e:  # noqa: BLE001 网络层异常一律重试
            last_err = e
            if verbose:
                print("[retry %d/%d] %s: %s" % (attempt + 1, RETRIES, type(e).__name__, e), file=sys.stderr)
            if attempt < RETRIES - 1:
                time.sleep(0.5 * (3 ** attempt))  # 0.5s / 1.5s / 4.5s
    raise LLMUnavailable("重试 %d 次仍失败: %s: %s" % (RETRIES, type(last_err).__name__, last_err))


def _extract_json(text: str):
    """从可能带 markdown 围栏的输出里抠出第一个 JSON 值。"""
    text = text.strip()
    if text.startswith(FENCE):
        text = text[len(FENCE):]
        if text[:4].lower() == "json":
            text = text[4:]
        text = text.strip()
    if text.endswith(FENCE):
        text = text[: -len(FENCE)].strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    start = min([i for i in (text.find("{"), text.find("[")) if i >= 0], default=-1)
    if start < 0:
        raise ValueError("输出中找不到 JSON")
    depth, in_str, esc = 0, False, False
    for i, ch in enumerate(text[start:], start=start):
        if in_str:
            if esc:
                esc = False
            elif ch == BS:
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "{[":
            depth += 1
        elif ch in "}]":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise ValueError("JSON 不完整")


def json_call(messages: list, system: str | None = None, **kw):
    """要求模型输出严格 JSON，返回 Python 对象（解析失败让模型自修一次）。"""
    text = call_llm(messages, system=system, **kw)
    try:
        return _extract_json(text)
    except Exception:
        repair = messages + [
            {"role": "assistant", "content": text},
            {"role": "user", "content": "上面的输出不是可解析的 JSON。只输出一个 JSON，不要任何解释或 markdown 围栏。"},
        ]
        return _extract_json(call_llm(repair, system=system, **kw))
