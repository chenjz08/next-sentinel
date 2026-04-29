#!/usr/bin/env python3
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


CODEX_HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
HOOKS_DIR = Path(os.environ.get("NEXT_HOOKS_DIR", CODEX_HOME / "hooks")).expanduser()
CONFIG_PATH = Path(os.environ.get("NEXT_ROUTER_CONFIG", HOOKS_DIR / "next_router_config.json")).expanduser()
DISABLED_PATH = Path(os.environ.get("NEXT_ROUTER_DISABLED", HOOKS_DIR / "NEXT_ROUTER_DISABLED")).expanduser()
LOG_PATH = Path(os.environ.get("NEXT_ROUTER_LOG", HOOKS_DIR / "next_router.log")).expanduser()
STATE_DIR = Path(os.environ.get("NEXT_ROUTER_STATE_DIR", HOOKS_DIR / ".next-router-state")).expanduser()

NEXT_PROTOCOL = """每轮最后一行写：
NEXT: 继续/实现/修复/审查/发布/停止
规则：未开始或不完整=继续；实现/修复完成=审查；审查有问题=修复；审查通过且还有开发=实现；准备交付=发布；结束=停止。"""

NEXT_RE = re.compile(r"^\s*NEXT:\s*(继续|实现|修复|审查|发布|停止)\s*$")


def default_skill_root():
    return Path(os.environ.get("NEXT_SKILL_ROOT", CODEX_HOME / "skills")).expanduser()


def skill_link(name, skill_root=None):
    root = Path(skill_root).expanduser() if skill_root else default_skill_root()
    return f"[${name}]({root / name / 'SKILL.md'})"


def build_messages(config=None):
    config = config or {}
    root = Path(config.get("skill_root") or default_skill_root()).expanduser()
    implementation = (
        skill_link("incremental-implementation", root)
        + "\n"
        + skill_link("test-driven-development", root)
        + "\n\n"
        + NEXT_PROTOCOL
    )
    return {
        "继续": "继续\n\n" + NEXT_PROTOCOL,
        "实现": implementation,
        "修复": implementation,
        "审查": skill_link("code-review-and-quality", root) + "\n\n" + NEXT_PROTOCOL,
        "发布": skill_link("shipping-and-launch", root) + "\n\n" + NEXT_PROTOCOL,
    }


MESSAGES = build_messages()


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


def log_event(payload, result, marker=None):
    line = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": "Stop",
        "result": result,
        "marker": marker,
        "session_id": payload.get("session_id"),
        "cwd": payload.get("cwd"),
        "turn_id": payload.get("turn_id"),
        "stop_hook_active": payload.get("stop_hook_active"),
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


def state_path(session_id):
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", session_id or "unknown")
    return STATE_DIR / f"{safe}.json"


def read_state(session_id):
    return load_json(state_path(session_id), {"count": 0, "last_turn_id": None})


def write_state(session_id, state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(state_path(session_id), "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def find_next_marker(message):
    if not message:
        return None
    lines = [line.strip() for line in message.splitlines() if line.strip()]
    if not lines:
        return None
    for line in reversed(lines):
        match = NEXT_RE.match(line)
        if match:
            return match.group(1)
    return None


def continue_with(reason):
    print(json.dumps({
        "decision": "block",
        "reason": reason
    }, ensure_ascii=False))


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return

    config = load_json(CONFIG_PATH, {})
    if DISABLED_PATH.exists():
        log_event(payload, "disabled")
        return
    if not enabled_for(payload, config):
        log_event(payload, "ignored")
        return

    marker = find_next_marker(payload.get("last_assistant_message"))
    session_id = payload.get("session_id") or "unknown"
    turn_id = payload.get("turn_id")

    if marker == "停止":
        write_state(session_id, {"count": 0, "last_turn_id": turn_id})
        log_event(payload, "stop", marker)
        return

    if marker is None:
        marker = "继续"

    reason = build_messages(config).get(marker)
    if not reason:
        log_event(payload, "unknown_marker", marker)
        return

    state = read_state(session_id)
    count = int(state.get("count") or 0)
    if state.get("last_turn_id") != turn_id:
        count += 1

    max_auto = int(config.get("max_auto_continuations") or 24)
    if count > max_auto:
        write_state(session_id, {"count": count, "last_turn_id": turn_id})
        log_event(payload, "max_auto", marker)
        return

    write_state(session_id, {"count": count, "last_turn_id": turn_id})
    log_event(payload, "continue", marker)
    continue_with(reason)


if __name__ == "__main__":
    main()
