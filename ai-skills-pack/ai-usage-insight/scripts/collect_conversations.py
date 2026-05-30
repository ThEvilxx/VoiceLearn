#!/usr/bin/env python3
"""Collect local AI conversations with metadata.

Outputs JSON array to stdout. Each entry:
  { "source": "collector id", "file": "...", "queries": [...],
    "rounds": N, "has_retry": bool, "mtime": "ISO" }

Usage:
  python3 collect_conversations.py --source all --project-root /path/to/project
  python3 collect_conversations.py --source cursor --project-root /path/to/project [projects_dir]
  python3 collect_conversations.py --source codex --project-root /path/to/project [sessions_root]
  python3 collect_conversations.py --source hermes --project-root /path/to/project [hermes_root]
  python3 collect_conversations.py --source claude-code --project-root /path/to/project [claude_projects_root]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, List

from _helpers import get_report_week_start, has_retry_signal, is_system_noise, normalize_topic


_PROJECT_TERMS_CACHE: dict[str, list[str]] = {}


def _project_markers(project_root: str | None) -> list[str]:
    if not project_root:
        return []
    root = os.path.abspath(project_root).rstrip("/")
    no_leading = root.lstrip("/")
    return [
        root,
        no_leading,
        no_leading.replace("/", "-"),
        no_leading.replace("/", "_"),
    ]


def _project_terms(project_root: str | None) -> list[str]:
    if not project_root:
        return []
    root = os.path.abspath(project_root).rstrip("/")
    if root in _PROJECT_TERMS_CACHE:
        return _PROJECT_TERMS_CACHE[root]

    terms: list[str] = []
    basename = Path(root).name
    if basename:
        terms.append(basename)

    readme = Path(root) / "README.md"
    try:
        text = readme.read_text(encoding="utf-8", errors="replace")[:4000]
    except OSError:
        text = ""
    for raw in text.splitlines()[:30]:
        line = raw.strip().strip("#").strip()
        if not line:
            continue
        for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}|[\u4e00-\u9fff]{2,8}", line):
            if token not in terms:
                terms.append(token)
        if len(terms) >= 12:
            break
    cjk_text = "".join(re.findall(r"[\u4e00-\u9fff]+", text[:800]))
    stop_terms = {"一个", "当前", "本地", "系统", "支持", "已经", "新增", "默认", "核心", "数据", "文件", "目录"}
    for size in (3, 4, 5):
        for i in range(max(len(cjk_text) - size + 1, 0)):
            term = cjk_text[i:i + size]
            if term in stop_terms:
                continue
            if "表情" in term or "微信" in term or "飞书" in term or "搜索" in term or "复制" in term:
                if term not in terms:
                    terms.append(term)
            if len(terms) >= 24:
                break
        if len(terms) >= 24:
            break

    _PROJECT_TERMS_CACHE[root] = terms
    return terms


def _text_mentions_project(text: str, project_root: str | None) -> bool:
    markers = _project_markers(project_root)
    terms = _project_terms(project_root)
    lowered = text.lower()
    return any(marker and marker.lower() in lowered for marker in markers) or any(term and term.lower() in lowered for term in terms)


def _path_matches_project(path: Path, project_root: str | None) -> bool:
    markers = _project_markers(project_root)
    if not markers:
        return True
    text = str(path)
    return any(marker and marker in text for marker in markers)


def _file_mentions_project(path: Path, project_root: str | None, limit: int = 200000) -> bool:
    markers = _project_markers(project_root)
    if not markers:
        return True
    try:
        text = path.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return False
    return any(marker and marker in text for marker in markers)


def _cursor_transcripts(projects_dir: str, monday_ts: float, project_root: str | None = None, include_unscoped: bool = False) -> List[dict[str, Any]]:
    results: List[dict[str, Any]] = []
    root = Path(projects_dir)
    if not root.exists():
        return results
    for proj in root.iterdir():
        if not proj.is_dir():
            continue
        project_dir_matches = _path_matches_project(proj, project_root)
        tdir = proj / "agent-transcripts"
        if not tdir.exists():
            continue
        for sub in tdir.iterdir():
            if not sub.is_dir() or sub.name == "subagents":
                continue
            for jf in sub.glob("*.jsonl"):
                if "subagents" in str(jf):
                    continue
                try:
                    mtime = jf.stat().st_mtime
                except OSError:
                    continue
                if mtime < monday_ts:
                    continue
                project_match = project_dir_matches or _file_mentions_project(jf, project_root)
                if project_root and not project_match and not include_unscoped:
                    continue
                queries, rounds, retry = _parse_cursor_jsonl(jf)
                if not queries:
                    continue
                results.append({
                    "source": "cursor",
                    "file": str(jf),
                    "queries": queries,
                    "rounds": rounds,
                    "has_retry": retry,
                    "mtime": datetime.fromtimestamp(mtime).isoformat(),
                    "project_match": project_match,
                })
    return results


def _parse_cursor_jsonl(path: Path) -> tuple[list[str], int, bool]:
    queries: list[str] = []
    rounds = 0
    retry = False
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("role") != "user":
                    continue
                content = entry.get("message", {}).get("content", "")
                if isinstance(content, list):
                    content = "\n".join(
                        i.get("text", "") for i in content
                        if isinstance(i, dict) and i.get("type") == "text"
                    )
                if is_system_noise(content):
                    continue
                rounds += 1
                matches = re.findall(r"<user_query>\s*(.*?)\s*</user_query>", content, re.DOTALL)
                for m in matches:
                    n = normalize_topic(m)
                    if n:
                        queries.append(n)
                    if has_retry_signal(m):
                        retry = True
    except (OSError, UnicodeDecodeError):
        pass
    return queries, rounds, retry


def _codex_sessions(sessions_root: str, monday_ts: float, workspace_prefix: str | None = None, include_unscoped: bool = False) -> List[dict[str, Any]]:
    results: List[dict[str, Any]] = []
    root = Path(sessions_root)
    if not root.is_dir():
        return results
    norm_prefix = None
    if workspace_prefix:
        norm_prefix = os.path.abspath(workspace_prefix).rstrip("/") + "/"
    for jf in sorted(root.rglob("rollout*.jsonl")):
        try:
            mtime = jf.stat().st_mtime
        except OSError:
            continue
        if mtime < monday_ts:
            continue
        cwd = _codex_cwd(jf) if norm_prefix else None
        project_match = True
        if norm_prefix:
            project_match = bool(cwd and (os.path.abspath(cwd).rstrip("/") + "/").startswith(norm_prefix))
            if not project_match and not include_unscoped:
                continue
        queries, rounds, retry = _parse_codex_jsonl(jf)
        if not queries:
            continue
        results.append({
            "source": "codex",
            "file": str(jf),
            "queries": queries,
                "rounds": rounds,
                "has_retry": retry,
                "mtime": datetime.fromtimestamp(mtime).isoformat(),
                "cwd": cwd,
                "project_match": project_match,
            })
    return results


def _codex_cwd(path: Path) -> str | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            for _ in range(80):
                line = f.readline()
                if not line:
                    break
                try:
                    entry = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue
                if entry.get("type") == "session_meta":
                    return (entry.get("payload") or {}).get("cwd")
    except (OSError, UnicodeDecodeError):
        pass
    return None


def _parse_codex_jsonl(path: Path) -> tuple[list[str], int, bool]:
    queries: list[str] = []
    rounds = 0
    retry = False
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("type") != "event_msg":
                    continue
                payload = entry.get("payload") or {}
                if payload.get("type") != "user_message":
                    continue
                text = payload.get("message", "")
                if not isinstance(text, str):
                    continue
                if is_system_noise(text):
                    continue
                rounds += 1
                n = normalize_topic(text)
                if n:
                    queries.append(n)
                if has_retry_signal(text):
                    retry = True
    except (OSError, UnicodeDecodeError):
        pass
    return queries, rounds, retry


def _message_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)
    if isinstance(value, dict):
        text = value.get("text") or value.get("content")
        return text if isinstance(text, str) else ""
    return ""


def _parse_iso_ts(text: str | None) -> float | None:
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _hermes_session_files(hermes_root: Path) -> list[tuple[Path, str]]:
    files: list[tuple[Path, str]] = []
    root_sessions = hermes_root / "sessions"
    if root_sessions.is_dir():
        for path in sorted(root_sessions.glob("session_*.json")):
            files.append((path, "default"))
        for path in sorted(root_sessions.glob("*.jsonl")):
            files.append((path, "default"))

    profiles_root = hermes_root / "profiles"
    if profiles_root.is_dir():
        for profile_dir in sorted(profiles_root.iterdir()):
            if not profile_dir.is_dir():
                continue
            sessions_dir = profile_dir / "sessions"
            if not sessions_dir.is_dir():
                continue
            for path in sorted(sessions_dir.glob("session_*.json")):
                files.append((path, profile_dir.name))
            for path in sorted(sessions_dir.glob("*.jsonl")):
                files.append((path, profile_dir.name))
    return files


def _hermes_sessions(hermes_root: str, monday_ts: float, project_root: str | None = None, include_unscoped: bool = False) -> List[dict[str, Any]]:
    results: List[dict[str, Any]] = []
    root = Path(hermes_root).expanduser()
    if not root.is_dir():
        return results

    for path, profile in _hermes_session_files(root):
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if mtime < monday_ts:
            continue
        project_match = _path_matches_project(path, project_root) or _file_mentions_project(path, project_root)
        if project_root and not project_match and not include_unscoped:
            continue
        if path.suffix == ".json":
            queries, rounds, retry = _parse_hermes_json(path)
        else:
            queries, rounds, retry = _parse_hermes_jsonl(path)
        if project_root and not _path_matches_project(path, project_root):
            queries = [q for q in queries if _text_mentions_project(q, project_root)]
            rounds = len(queries)
            retry = any(has_retry_signal(q) for q in queries)
        if not queries:
            continue
        results.append({
            "source": "hermes",
            "profile": profile,
            "file": str(path),
            "queries": queries,
            "rounds": rounds,
            "has_retry": retry,
            "mtime": datetime.fromtimestamp(mtime).isoformat(),
            "project_match": project_match,
        })
    return results


def _parse_hermes_json(path: Path) -> tuple[list[str], int, bool]:
    queries: list[str] = []
    rounds = 0
    retry = False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return queries, rounds, retry
    messages = data.get("messages")
    if not isinstance(messages, list):
        return queries, rounds, retry
    for msg in messages:
        if not isinstance(msg, dict) or msg.get("role") != "user":
            continue
        text = _message_text(msg.get("content"))
        if is_system_noise(text):
            continue
        rounds += 1
        n = normalize_topic(text)
        if n:
            queries.append(n)
        if has_retry_signal(text):
            retry = True
    return queries, rounds, retry


def _parse_hermes_jsonl(path: Path) -> tuple[list[str], int, bool]:
    queries: list[str] = []
    rounds = 0
    retry = False
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("role") != "user":
                    continue
                text = _message_text(entry.get("content") or entry.get("message"))
                if is_system_noise(text):
                    continue
                rounds += 1
                n = normalize_topic(text)
                if n:
                    queries.append(n)
                if has_retry_signal(text):
                    retry = True
    except (OSError, UnicodeDecodeError):
        pass
    return queries, rounds, retry


def _claude_code_sessions(projects_root: str, monday_ts: float, project_root: str | None = None, include_unscoped: bool = False) -> List[dict[str, Any]]:
    results: List[dict[str, Any]] = []
    root = Path(projects_root).expanduser()
    if not root.is_dir():
        return results
    for jf in sorted(root.rglob("*.jsonl")):
        try:
            mtime = jf.stat().st_mtime
        except OSError:
            continue
        if mtime < monday_ts:
            continue
        project_match = _path_matches_project(jf, project_root) or _file_mentions_project(jf, project_root)
        if project_root and not project_match and not include_unscoped:
            continue
        queries, rounds, retry, cwd = _parse_claude_code_jsonl(jf)
        if not queries:
            continue
        results.append({
            "source": "claude-code",
            "file": str(jf),
            "queries": queries,
            "rounds": rounds,
            "has_retry": retry,
            "mtime": datetime.fromtimestamp(mtime).isoformat(),
            "cwd": cwd,
            "project_match": project_match,
        })
    return results


def _parse_claude_code_jsonl(path: Path) -> tuple[list[str], int, bool, str | None]:
    queries: list[str] = []
    rounds = 0
    retry = False
    cwd: str | None = None
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if cwd is None:
                    for key in ("cwd", "workingDirectory", "projectCwd"):
                        value = entry.get(key)
                        if isinstance(value, str) and value:
                            cwd = value
                            break
                entry_type = entry.get("type")
                role = entry.get("role")
                message = entry.get("message")
                if isinstance(message, dict):
                    role = role or message.get("role")
                if role != "user" and entry_type not in {"user", "user_message"}:
                    continue
                text = _message_text(entry.get("content"))
                if not text and isinstance(message, dict):
                    text = _message_text(message.get("content"))
                if not text:
                    text = _message_text(entry.get("text") or entry.get("prompt"))
                if is_system_noise(text):
                    continue
                rounds += 1
                n = normalize_topic(text)
                if n:
                    queries.append(n)
                if has_retry_signal(text):
                    retry = True
    except (OSError, UnicodeDecodeError):
        pass
    return queries, rounds, retry, cwd


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["cursor", "codex", "hermes", "claude-code", "all"], default="all")
    parser.add_argument("--project-root", default=os.getcwd(),
                        help="只采集与该项目路径匹配的对话；默认使用当前目录")
    parser.add_argument("--include-unscoped", action="store_true",
                        help="同时包含无法识别项目归属的对话，默认不包含")
    parser.add_argument("positional", nargs="*")
    args = parser.parse_args(argv[1:])

    monday_ts = get_report_week_start().timestamp()
    results: list[dict[str, Any]] = []

    if args.source in ("cursor", "all"):
        cursor_dir = args.positional[0] if args.positional else os.path.expanduser("~/.cursor/projects")
        results.extend(_cursor_transcripts(cursor_dir, monday_ts, args.project_root, args.include_unscoped))

    if args.source in ("codex", "all"):
        codex_dir = os.environ.get("CODEX_SESSIONS_DIR", "").strip()
        if not codex_dir:
            codex_dir = str(Path.home() / ".codex" / "sessions")
        if args.source == "codex" and args.positional:
            codex_dir = args.positional[0]
        wp = args.project_root
        if len(args.positional) > 1 and args.source == "codex":
            wp = args.positional[1]
        results.extend(_codex_sessions(codex_dir, monday_ts, wp, args.include_unscoped))

    if args.source in ("hermes", "all"):
        hermes_root = os.environ.get("HERMES_HOME", "").strip()
        if not hermes_root:
            hermes_root = str(Path.home() / ".hermes")
        if args.source == "hermes" and args.positional:
            hermes_root = args.positional[0]
        results.extend(_hermes_sessions(hermes_root, monday_ts, args.project_root, args.include_unscoped))

    if args.source in ("claude-code", "all"):
        claude_projects = os.environ.get("CLAUDE_PROJECTS_DIR", "").strip()
        if not claude_projects:
            claude_home = os.environ.get("CLAUDE_HOME", "").strip()
            claude_projects = str((Path(claude_home).expanduser() if claude_home else Path.home() / ".claude") / "projects")
        if args.source == "claude-code" and args.positional:
            claude_projects = args.positional[0]
        results.extend(_claude_code_sessions(claude_projects, monday_ts, args.project_root, args.include_unscoped))

    json.dump(results, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
