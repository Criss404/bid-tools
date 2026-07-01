#!/usr/bin/env python3
"""AI 统一入口 — 所有 AI 调用走这里

配置: ai.yml（用户在 GUI 设置弹窗填写）
"""

import os
import yaml
from openai import OpenAI

_CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".bid_tool", "ai.yml")


def _load_config() -> dict:
    """读 ai.yml，带默认值"""
    if os.path.exists(_CONFIG_PATH):
        try:
            cfg = yaml.safe_load(open(_CONFIG_PATH, encoding="utf-8")) or {}
            return cfg
        except Exception:
            pass
    return {}


def _save_config(cfg: dict):
    """写 ai.yml"""
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False)


def get_config() -> dict:
    """返回当前 AI 配置"""
    cfg = _load_config()
    return {
        "key": cfg.get("key", "").strip(),
        "url": cfg.get("url", "https://api.deepseek.com").strip(),
        "model": cfg.get("model", "deepseek-chat").strip(),
    }


def update_config(key: str = "", url: str = "", model: str = ""):
    """更新 AI 配置"""
    cfg = _load_config()
    if key is not None:
        cfg["key"] = key.strip()
    if url is not None:
        cfg["url"] = url.strip() or "https://api.deepseek.com"
    if model is not None:
        cfg["model"] = model.strip() or "deepseek-chat"
    _save_config(cfg)


def is_ready() -> bool:
    """AI 是否已配置 Key"""
    return bool(get_config()["key"])


def test_connection(key: str = "", url: str = "", model: str = "") -> str:
    """测试 AI 连接，返回 "OK" 或错误信息"""
    cfg = get_config()
    test_key = key.strip() or cfg["key"]
    test_url = url.strip() or cfg["url"]
    test_model = model.strip() or cfg["model"]

    if not test_key:
        return "未配置 API Key"

    try:
        client = OpenAI(api_key=test_key, base_url=test_url)
        resp = client.chat.completions.create(
            model=test_model,
            messages=[{"role": "user", "content": "回复 OK"}],
            max_tokens=10)
        return f"连接成功 ({test_model})"
    except Exception as e:
        msg = str(e)
        if "401" in msg or "auth" in msg.lower():
            return "Key 无效 (401)"
        if "404" in msg:
            return f"模型不可用: {test_model}"
        if "timeout" in msg.lower() or "connect" in msg.lower():
            return "网络不通，请检查 URL 和网络"
        return f"失败: {msg[:80]}"


def chat(messages: list[dict], **kwargs) -> str:
    """统一 AI 调用入口。

    Args:
        messages: [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
        **kwargs: temperature, max_tokens 等

    Returns:
        AI 返回的文本

    Raises:
        RuntimeError: Key 未配置时
        Exception: 网络/API 错误时
    """
    cfg = get_config()
    if not cfg["key"]:
        raise RuntimeError(
            "AI API Key 未配置。\n"
            "请点击 AI 分析页面的「设置」按钮填入 Key。\n"
            "注册获取: https://platform.deepseek.com/"
        )

    client = OpenAI(api_key=cfg["key"], base_url=cfg["url"])

    temperature = kwargs.pop("temperature", 0.3)
    max_tokens = kwargs.pop("max_tokens", 4096)

    response = client.chat.completions.create(
        model=cfg["model"],
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs
    )
    return response.choices[0].message.content
