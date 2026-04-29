#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


CODEX_HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
HOOKS_DIR = Path(os.environ.get("NEXT_HOOKS_DIR", CODEX_HOME / "hooks")).expanduser()
CONFIG_PATH = Path(os.environ.get("NEXT_ROUTER_CONFIG", HOOKS_DIR / "next_router_config.json")).expanduser()
DISABLED_PATH = Path(os.environ.get("NEXT_ROUTER_DISABLED", HOOKS_DIR / "NEXT_ROUTER_DISABLED")).expanduser()
LOG_PATH = Path(os.environ.get("NEXT_ROUTER_LOG", HOOKS_DIR / "next_router.log")).expanduser()

NEXT_PROTOCOL = """每轮最后一行写：
NEXT: 继续/实现/修复/审查/发布/停止
规则：未开始或不完整=继续；实现/修复完成=审查；审查有问题=修复；审查通过且还有开发=实现；准备交付=发布；结束=停止。"""


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def normalize_path(path):
    if not path:
        return ""
    return os.path.abspath(os.path.expanduser(path))


def log_event(payload, result):
    line = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": "SessionStart",
        "result": result,
        "session_id": payload.get("session_id"),
        "cwd": payload.get("cwd"),
        "source": payload.get("source"),
    }
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    except Exception:
        pass


def enabled_for(payload, config):
    session_id = payload.get("session_id")
    cwd = normalize_path(payload.get("cwd"))

    target_sessions = set(config.get("target_sessions") or [])
    target_cwds = {normalize_path(p) for p in (config.get("target_cwds") or [])}

    if session_id and session_id in target_sessions:
        return True
    return bool(cwd and cwd in target_cwds)


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}

    config = load_json(CONFIG_PATH, {})
    if DISABLED_PATH.exists():
        log_event(payload, "disabled")
        return
    if not enabled_for(payload, config):
        log_event(payload, "ignored")
        return

    log_event(payload, "inject")
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": NEXT_PROTOCOL
        }
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
