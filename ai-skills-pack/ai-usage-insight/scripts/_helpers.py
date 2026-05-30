"""Shared helpers for ai-usage-insight scripts."""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Iterable, List, Optional


LOW_SIGNAL_PATTERNS = [
    r"^(可以|可行|继续吧|继续|执行吧|执行|行|好的|好|测试|准了)$",
    r"^(ok|okay|收到|明白了|先这样吧|会话记录)[。！!，, ]*$",
    r"^(可行[，, ]*)?继续吧[。！!，, ]*$",
    r"^(ok|okay)[，, ]*测试一下[。！!，, ]*$",
    r"^本地测试[，, ]*没问题就提交代码吧[。！!，, ]*$",
    r"^不需要草案[。！!，, ]*$",
    r"^周报[。！!，, ]*$",
    r"^可以[，, ]*编写计划任务吧[，, ]*继续完善[。！!，, ]*$",
]

SYSTEM_NOISE_PREFIXES = [
    "The following is the Codex agent history whose request action you are assessing.",
    "The following is the Codex agent history added since your last approval assessment.",
    "Review the conversation above",
    "[CONTEXT COMPACTION",
    "[Workspace::v1:",
]

RETRY_KEYWORDS = [
    "再试", "不对", "重新做", "重来", "wrong", "retry", "try again",
    "还是不行", "不对吧", "错了", "有问题", "fix this", "重新生成",
    "这不对", "不是这样", "not right", "incorrect",
]


def get_report_week_start() -> datetime:
    today = datetime.now()
    days_since_monday = today.weekday()
    monday = today - timedelta(days=days_since_monday)
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    if days_since_monday == 0:
        monday = monday - timedelta(days=7)
    return monday


def is_low_signal(text: str) -> bool:
    stripped = text.strip().lower()
    if not stripped:
        return True
    for pattern in LOW_SIGNAL_PATTERNS:
        if re.fullmatch(pattern, stripped, flags=re.IGNORECASE):
            return True
    if len(stripped) <= 12 and any(t in stripped for t in ["继续", "可行", "测试一下", "授权", "开始执行"]):
        return True
    return False


def is_system_noise(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    return any(stripped.startswith(prefix) for prefix in SYSTEM_NOISE_PREFIXES)


def has_retry_signal(text: str) -> bool:
    if is_system_noise(text):
        return False
    lower = text.lower()
    return any(kw in lower for kw in RETRY_KEYWORDS)


def normalize_topic(text: str) -> Optional[str]:
    text = re.sub(r"</?user_query>", "", text, flags=re.IGNORECASE).strip()
    if is_system_noise(text):
        return None
    text = text.replace("\u3000", " ")
    text = re.sub(r"\r\n?", "\n", text).strip()
    if not text:
        return None
    lines = [
        l.strip()
        for l in text.split("\n")
        if l.strip() and not is_system_noise(l.strip())
    ]
    if not lines:
        return None
    combined = "；".join(lines[:3])
    combined = re.sub(r"\s+", " ", combined).strip()
    if is_system_noise(combined):
        return None
    if is_low_signal(combined):
        return None
    return combined


def deduplicate_topics(topics: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    result: List[str] = []
    for topic in topics:
        n = normalize_topic(topic)
        if not n:
            continue
        key = n[:160].lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(n)
    return result
