# Next Sentinel

[中文](README.md)

Next Sentinel is a macOS menu bar tool for long-running Codex sessions.

It exists because long Codex tasks run into two practical problems:

1. Heartbeat automations spend extra tokens. Each run has to restore the session, read context, and decide what to do. The longer the task runs, the more waste you get from idle checks.
2. A generic automation often guesses the next step. Without a small protocol, it may keep implementing when the work needs review, or publish when the last review found bugs.

Next Sentinel uses Codex hooks as the main path and keeps automation as a restart fallback. During normal work, Codex `SessionStart` and `Stop` hooks inject the rule, read the latest result, and route the next step. When Codex restarts or the hooks miss a transition, the menu bar app triggers `automation-2` once.

This makes continuation event-driven instead of a minute-by-minute polling loop.

## Who It Is For

- You run long Codex tasks and want them to move through implementation, review, fixes, and release without manual nudging.
- You want fewer token-wasting heartbeat runs.
- You want the agent to state the next step instead of leaving the automation to infer it.
- You use local skills and want each phase to map to a concrete engineering workflow.
- You switch Codex accounts with Cockpit Tools or restart Codex during the day, and you need one fallback run after Codex comes back.

## Core Idea

At the end of each turn, the agent leaves one `NEXT:` marker:

```text
NEXT: 继续
NEXT: 实现
NEXT: 修复
NEXT: 审查
NEXT: 发布
NEXT: 停止
```

`next_stop_router.py` scans the latest assistant output from the bottom and uses the last explicit marker:

| Marker | Next message |
| --- | --- |
| `NEXT: 继续` | Plain text: `继续` |
| `NEXT: 实现` | `incremental-implementation` and `test-driven-development` |
| `NEXT: 修复` | `incremental-implementation` and `test-driven-development` |
| `NEXT: 审查` | `code-review-and-quality` |
| `NEXT: 发布` | `shipping-and-launch` |
| `NEXT: 停止` | Send nothing |

The TDD and incremental workflow come from [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills), a set of production-grade engineering skills for AI coding agents. This project uses `test-driven-development`, `incremental-implementation`, `code-review-and-quality`, and `shipping-and-launch`.

`test-driven-development` makes the agent prove behavior with tests before or while changing code. `incremental-implementation` keeps large work in small slices: implement, test, verify, commit, then continue. Next Sentinel connects those skills to the Codex session lifecycle through the `NEXT:` protocol.

## Why Hooks Matter

Heartbeat automation runs on time. It may fire when the target session still runs, when nothing needs to happen, or when the last output did not contain a usable decision.

Hooks line up with the actual session lifecycle:

- `SessionStart` injects the NEXT protocol only when a session starts, resumes, or clears.
- `Stop` runs right after a turn finishes, when the latest `NEXT:` marker is available.
- The router sends fixed messages, so the fallback automation does not invent the next step.
- `max_auto_continuations` limits runaway continuation.
- `automation-2` stays `PAUSED` during normal use and only wakes up for a restart fallback.

The daily path is hooks. The restart path is a one-shot automation. The menu bar app watches the bridge between them.

## Features

- Menu bar app named `NEXT`.
- Watches the Codex App bundle identifier: `com.openai.codex`.
- Waits 60 seconds after Codex starts before triggering the fallback, giving Codex time to initialize and load account state.
- Shows hook status, automation status, schedule, next run time, and recent actions.
- Provides actions for starting NEXT, stopping NEXT, triggering fallback, opening logs, and opening the hooks directory.
- Includes the Codex hook scripts: `next_session_start.py`, `next_stop_router.py`, and `next_ctl.py`.
- Includes installation scripts, a Codex restart script, configuration examples, an `automation-2` example, and tests.
- Documents the Cockpit Tools account-switch path without storing real accounts or tokens.

## How It Works

Normal hook path:

```text
Codex session starts or resumes
      |
      v
SessionStart hook injects the NEXT protocol
      |
      v
Agent runs the task and writes a NEXT marker
      |
      v
Stop hook reads the last explicit NEXT marker
      |
      v
Router sends plain text or a skill link
      |
      v
Next turn runs under the matching skill
```

Restart fallback path:

```text
Cockpit Tools switches Codex account (optional)
      |
      v
Codex App restarts
      |
      v
Next Sentinel sees Codex start
      |
      v
Wait 60 seconds
      |
      v
next_ctl.py trigger schedules automation-2 once
      |
      v
automation-2 resumes the target session
      |
      v
Target session still running: send nothing
Target session can continue: route by the latest NEXT marker
      |
      v
automation-2 returns to PAUSED
```

See [docs/usage-associations.md](docs/usage-associations.md) for the full object map.

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/ouyanggai/next-sentinel.git
cd next-sentinel
```

### 2. Install the hook scripts

```bash
./scripts/install-hooks.sh
```

The script copies these files to `~/.codex/hooks/`:

```text
next_ctl.py
next_session_start.py
next_stop_router.py
```

If you use a different Codex home:

```bash
CODEX_HOME="$HOME/.codex" ./scripts/install-hooks.sh
```

### 3. Configure Codex hooks

Merge `examples/config.toml.snippet` into `~/.codex/config.toml`:

```toml
[features]
codex_hooks = true

[[hooks.SessionStart]]
matcher = "startup|resume|clear"

[[hooks.SessionStart.hooks]]
type = "command"
command = "python3 ~/.codex/hooks/next_session_start.py"
timeout = 10
statusMessage = "Loading NEXT protocol"

[[hooks.Stop]]

[[hooks.Stop.hooks]]
type = "command"
command = "python3 ~/.codex/hooks/next_stop_router.py"
timeout = 30
statusMessage = "Routing NEXT"
```

If your Codex build does not expand `~`, use absolute paths.

### 4. Configure target sessions and project directories

Edit:

```text
~/.codex/hooks/next_router_config.json
```

Example:

```json
{
  "target_sessions": [
    "replace-with-target-session-id"
  ],
  "target_cwds": [
    "/absolute/path/to/your/project"
  ],
  "max_auto_continuations": 24,
  "skill_root": "~/.codex/skills"
}
```

`target_sessions` pins routing to a long-running session. `target_cwds` pins routing to a project directory. The hook runs when either one matches.

### 5. Configure `automation-2`

Create the directory:

```bash
mkdir -p ~/.codex/automations/automation-2
```

Use `examples/automation-2.toml` as the starting point:

```text
~/.codex/automations/automation-2/automation.toml
```

Keep these settings clear:

- `status` should default to `PAUSED`.
- `rrule` can stay as `FREQ=MINUTELY;INTERVAL=1`, but idle state should not stay active.
- The prompt should only route by `NEXT:` when the target session can receive input.
- If the target session still runs, the automation should send nothing.
- After the fallback finishes, `automation-2` should pause itself.

### 6. Build the menu bar app

Requirements:

- macOS 13 or newer.
- Xcode Command Line Tools for `swiftc` and `iconutil`.
- Python 3.
- Pillow for icon rendering.

Install Pillow:

```bash
python3 -m pip install pillow
```

Build and install to `~/Applications/Next Sentinel.app`:

```bash
./build.sh
```

Launch it:

```bash
open "$HOME/Applications/Next Sentinel.app"
```

Install somewhere else:

```bash
NEXT_SENTINEL_INSTALL_DIR="/Applications" ./build.sh
```

## Daily Use

Check status:

```bash
python3 ~/.codex/hooks/next_ctl.py status
```

Enable NEXT:

```bash
python3 ~/.codex/hooks/next_ctl.py start
```

Pause NEXT:

```bash
python3 ~/.codex/hooks/next_ctl.py stop
```

Trigger one fallback run:

```bash
python3 ~/.codex/hooks/next_ctl.py trigger
```

In the target session, ask the agent to end each turn with a clear marker:

```text
NEXT: 审查
```

The next turn receives the `code-review-and-quality` skill link. Implementation and fix stages receive both `incremental-implementation` and `test-driven-development`.

## Cockpit Account Switching and Codex Restart

Cockpit Tools is an external app. This repository does not call private Cockpit APIs or store real auth data.

On a local machine, Cockpit Tools may maintain a state file like:

```text
~/.codex/.cockpit_codex_auth.json
```

This repository only includes a placeholder example:

```text
examples/cockpit_codex_auth.example.json
```

After switching accounts, restart Codex:

```bash
./scripts/restart-codex.sh
```

If Next Sentinel is running, it sees Codex start and triggers `automation-2` after 60 seconds. This helps when Codex needs a restart to load the new account state.

## Status Output

`next_ctl.py status` prints something like:

```text
NEXT hooks: ACTIVE
codex_hooks feature: True
SessionStart hook: True
Stop hook: True
automation-2 toml: PAUSED
automation-2 db: PAUSED
automation-2 schedule: FREQ=MINUTELY;INTERVAL=1
automation-2 next_run_at: UNKNOWN
```

Read these fields first:

- `NEXT hooks: ACTIVE` means NEXT routing is enabled.
- `NEXT hooks: STOPPED` means `NEXT_ROUTER_DISABLED` paused routing.
- `automation-2 db: PAUSED` means the fallback automation is idle.
- `automation-2 db: ACTIVE` means one fallback run is waiting to execute.

## Tests

Tests live under `test/`:

```bash
python3 -m unittest discover -s test -p 'test_*.py'
```

Coverage includes:

- `NEXT: 实现` still routes to implementation when extra context follows it.
- Multiple `NEXT:` markers use the last explicit marker.
- The protocol choice line is not treated as a marker.
- Implementation and fix routes send both skill links instead of falling back to `继续`.
- `automation-2` returns to `PAUSED` after a one-shot trigger.

## Project Layout

```text
next-sentinel/
  Assets/                         # Menu bar and app icon assets
  Sources/                        # AppKit menu bar app
  hooks/                          # Codex hooks and control script
  scripts/                        # Hook installer and Codex restart helper
  examples/                       # Config, automation, and Cockpit examples
  docs/                           # Usage associations and workflow notes
  test/next_router/               # Hook routing and one-shot automation tests
  build.sh
  README.md
  README.en.md
```

Build output goes to `build/` and `dist/`; neither directory is tracked.

## Credits

This project uses the TDD, incremental implementation, review, and shipping workflow from [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills). That repository packages production-grade engineering workflows as Markdown skill files, which makes them easy to connect to Codex and Claude Code.

The local skill setup also works with Jim Liu's [baoyu-skills](https://github.com/jimliu/baoyu-skills). Keep these credits if you redistribute this project.

## Safety

- Do not commit `~/.codex/.cockpit_codex_auth.json`.
- Do not commit Codex `auth.json`, sqlite databases, real session state, or logs.
- Values in `examples/` are placeholders.
- Hook scripts read `$HOME/.codex` by default and support `CODEX_HOME`, `NEXT_HOOKS_DIR`, and `NEXT_SKILL_ROOT`.

## License

MIT
