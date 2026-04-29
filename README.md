# Next Sentinel

[English](README.en.md)

Next Sentinel 是一个给 Codex 长程任务用的 macOS 状态栏工具。

Next Sentinel 处理的是 Codex 长任务自动推进里的两个实际问题：

1. 纯自动化任务会额外消耗 token。定时心跳每跑一次都要恢复会话、读上下文、做判断。任务越长，空转成本越高。
2. 自动化不一定知道下一步该怎么推进。它看到的是一段历史输出，如果没有明确协议，很容易把该审查的任务继续实现，把该修复的任务直接发布。

Next Sentinel 的思路是让 hooks 做主链路，让自动化只做 Codex 重启后的兜底。平时依靠 Codex 的 `SessionStart` 和 `Stop` hook 自动注入规则、读取结果、分发下一步；只有 Codex 重启、hooks 没接上、会话卡住时，才由状态栏工具单次触发 `automation-2` 补一脚。

这样能把自动推进变成事件驱动，而不是每分钟轮询。

## 适合什么场景

- 你在 Codex 里跑一个很长的开发任务，希望它按“实现、审查、修复、发布”的节奏自己往前走。
- 你不想让自动化心跳一直消耗 token。
- 你希望每一轮结束后都有明确的下一步，而不是让模型猜。
- 你会用本地 skills，把不同阶段绑定到不同工程纪律上。
- 你有重启 Codex、Cockpit Tools 切号这类场景，需要 Codex 启动后自动恢复一次推进。

## 核心方案

每轮任务结束时，Agent 在最后留下一个 `NEXT:` 标识：

```text
NEXT: 继续
NEXT: 实现
NEXT: 修复
NEXT: 审查
NEXT: 发布
NEXT: 停止
```

`next_stop_router.py` 会从最近输出底部向上找最后一个明确标识，然后发送对应内容：

| 标识 | 下一步 |
| --- | --- |
| `NEXT: 继续` | 发送纯文字 `继续` |
| `NEXT: 实现` | 发送 `incremental-implementation` 和 `test-driven-development` 两个技能 |
| `NEXT: 修复` | 发送 `incremental-implementation` 和 `test-driven-development` 两个技能 |
| `NEXT: 审查` | 发送 `code-review-and-quality` 技能 |
| `NEXT: 发布` | 发送 `shipping-and-launch` 技能 |
| `NEXT: 停止` | 不再发送内容 |

这里的 TDD 和增量实现方案来自 [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills)。这个仓库把工程流程拆成可复用的 agent skills，本项目用到的是其中的 `test-driven-development`、`incremental-implementation`、`code-review-and-quality`、`shipping-and-launch` 这几类工作流。

`test-driven-development` 负责让模型先用测试证明行为，再写实现；`incremental-implementation` 负责把大任务拆成小切片，每个切片都要实现、测试、验证、提交。Next Sentinel 做的事情，是把这些技能接到 Codex 的会话生命周期里，让它们按 `NEXT:` 协议自动衔接。

## hooks 自动运行的好处

纯自动化心跳的问题是成本和判断都不稳定。它按时间跑，不管会话有没有真的需要继续，也不管上一轮是不是还在运行。

hooks 更适合做主链路：

- `SessionStart` 只在会话启动、恢复、清空时注入 NEXT 协议，不占用每分钟心跳。
- `Stop` 只在一轮回答结束后运行，刚好能读取这轮最后的 `NEXT:` 标识。
- 路由逻辑固定，不让自动化临场猜下一步。
- `max_auto_continuations` 可以限制连续自动推进次数，避免无限续跑。
- `automation-2` 平时保持 `PAUSED`，只在 Codex 重启后由 Next Sentinel 单次触发。

日常推进靠 hooks，重启兜底靠自动化，状态栏工具负责把这条链路看住。

## 功能

- macOS 状态栏常驻，显示为 `NEXT`。
- 监听 Codex App 的 bundle identifier：`com.openai.codex`。
- Codex 启动后等待 60 秒，再触发一次兜底，给 Codex 初始化和账号状态加载留时间。
- 菜单里可以查看 hooks 状态、自动化状态、调度信息、下次运行时间和最近动作。
- 支持手动启动 NEXT、停止 NEXT、立即触发兜底、打开日志、打开 hooks 目录。
- 提供完整 hook 脚本：`next_session_start.py`、`next_stop_router.py`、`next_ctl.py`。
- 提供安装脚本、重启 Codex 脚本、配置示例、自动化示例和测试用例。
- 记录 Cockpit Tools 自动切号与 Codex 重启的接入方式，但不保存真实账号或 token。

## 工作原理

```text
Codex 会话启动或恢复
      |
      v
SessionStart hook 注入 NEXT 协议
      |
      v
Agent 执行当前任务，并在最后写 NEXT 标识
      |
      v
Stop hook 读取最后一个明确 NEXT 标识
      |
      v
按标识发送继续文字或技能引用
      |
      v
下一轮按对应技能继续执行
```

Codex 重启后的兜底链路：

```text
Cockpit Tools 切换 Codex 账号（可选）
      |
      v
重启 Codex App
      |
      v
Next Sentinel 监听到 Codex 启动
      |
      v
等待 60 秒
      |
      v
next_ctl.py trigger 单次调度 automation-2
      |
      v
automation-2 恢复目标会话
      |
      v
目标会话仍在运行：不发送任何内容
目标会话可继续输入或已完成：读取最近输出，按 NEXT 标识分发
      |
      v
automation-2 回到 PAUSED
```

更完整的对象关联见 [docs/usage-associations.md](docs/usage-associations.md)。

## 安装

### 1. 克隆仓库

```bash
git clone https://github.com/ouyanggai/next-sentinel.git
cd next-sentinel
```

### 2. 安装 hook 脚本

```bash
./scripts/install-hooks.sh
```

脚本会复制这三个文件到 `~/.codex/hooks/`：

```text
next_ctl.py
next_session_start.py
next_stop_router.py
```

如果你用的不是默认 Codex 目录，可以提前设置：

```bash
CODEX_HOME="$HOME/.codex" ./scripts/install-hooks.sh
```

### 3. 配置 Codex hooks

把 `examples/config.toml.snippet` 合并到 `~/.codex/config.toml`：

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

如果你的 Codex 版本不展开 `~`，把命令改成绝对路径。

### 4. 配置目标会话和项目目录

编辑：

```text
~/.codex/hooks/next_router_config.json
```

示例：

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

`target_sessions` 适合锁定某个长程会话，`target_cwds` 适合锁定某个项目目录。命中任意一个条件，hook 就会启用 NEXT 路由。

### 5. 配置 `automation-2`

创建目录：

```bash
mkdir -p ~/.codex/automations/automation-2
```

参考 `examples/automation-2.toml` 创建：

```text
~/.codex/automations/automation-2/automation.toml
```

关键点：

- `status` 默认保持 `PAUSED`。
- `rrule` 可以保留 `FREQ=MINUTELY;INTERVAL=1`，但空闲时不能保持 active。
- prompt 要写清楚：只有目标会话可继续时才按 `NEXT:` 分发，目标会话仍运行时不发送内容。
- 兜底处理完后要把 `automation-2` 暂停。

### 6. 构建状态栏 App

环境要求：

- macOS 13 或更新版本。
- Xcode Command Line Tools，用于 `swiftc` 和 `iconutil`。
- Python 3。
- Pillow，用于渲染图标。

安装 Pillow：

```bash
python3 -m pip install pillow
```

构建并安装到 `~/Applications/Next Sentinel.app`：

```bash
./build.sh
```

启动：

```bash
open "$HOME/Applications/Next Sentinel.app"
```

如果要安装到其他目录：

```bash
NEXT_SENTINEL_INSTALL_DIR="/Applications" ./build.sh
```

## 日常使用

先确认状态：

```bash
python3 ~/.codex/hooks/next_ctl.py status
```

启用 NEXT：

```bash
python3 ~/.codex/hooks/next_ctl.py start
```

暂停 NEXT：

```bash
python3 ~/.codex/hooks/next_ctl.py stop
```

手动触发一次兜底：

```bash
python3 ~/.codex/hooks/next_ctl.py trigger
```

在目标会话里，让 Agent 每轮结束前写一个明确标识：

```text
NEXT: 审查
```

下一轮就会收到 `code-review-and-quality` 技能引用。实现和修复阶段会收到 `incremental-implementation` 与 `test-driven-development` 两个技能引用。

## Cockpit 自动切号与 Codex 重启

Cockpit Tools 是外部工具，本仓库不调用未公开 API，也不保存真实认证内容。

本机链路里，Cockpit Tools 会维护类似下面的状态文件：

```text
~/.codex/.cockpit_codex_auth.json
```

仓库只提供字段示例：

```text
examples/cockpit_codex_auth.example.json
```

切号完成后重启 Codex：

```bash
./scripts/restart-codex.sh
```

如果 Next Sentinel 已运行，它会监听 Codex 启动，并在 60 秒后触发一次 `automation-2`。这一步适合处理切号后 Codex 需要重新加载账号状态的场景。

## 状态说明

`next_ctl.py status` 会输出类似信息：

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

重点看这几项：

- `NEXT hooks: ACTIVE` 表示 NEXT 路由启用。
- `NEXT hooks: STOPPED` 表示通过 `NEXT_ROUTER_DISABLED` 暂停路由。
- `automation-2 db: PAUSED` 表示兜底自动化空闲。
- `automation-2 db: ACTIVE` 表示正在等待本次单次触发执行。

## 测试

测试用例放在 `test/` 目录：

```bash
python3 -m unittest discover -s test -p 'test_*.py'
```

测试覆盖：

- `NEXT: 实现` 后面有其他上下文时，仍按 `实现` 路由。
- 多个 `NEXT:` 标识时，使用最后一个明确标识。
- 协议说明行不会被误判为标识。
- `实现` 和 `修复` 会发送两个技能引用，不会降级成 `继续`。
- `automation-2` 单次触发后会回到 `PAUSED`。

## 目录结构

```text
next-sentinel/
  Assets/                         # 状态栏和 App 图标素材
  Sources/                        # AppKit 状态栏应用
  hooks/                          # Codex hook 和控制脚本
  scripts/                        # 安装 hooks、重启 Codex 的辅助脚本
  examples/                       # config、automation、cockpit 状态示例
  docs/                           # 使用关联和流程说明
  test/next_router/               # hook 路由与 automation 单次触发测试
  build.sh
  README.md
```

构建产物会生成到 `build/` 和 `dist/`，不会纳入 Git。

## 致谢

本项目的 TDD、增量实现、审查和发布阶段参考并使用了 [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) 的 skills 设计。这个仓库把生产级工程流程封装成 Markdown 技能文件，很适合接入 Codex、Claude Code 这类 agent。

本地技能生态也兼容宝玉大神 Jim Liu 的 [baoyu-skills](https://github.com/jimliu/baoyu-skills)。如果你继续分发本项目，请保留这些来源说明。

## 安全说明

- 不提交 `~/.codex/.cockpit_codex_auth.json`。
- 不提交 Codex 的 `auth.json`、sqlite 数据库、真实 session 状态和日志。
- `examples/` 里的 session、cwd、账号字段都是占位示例。
- hook 脚本默认读取 `$HOME/.codex`，也支持用 `CODEX_HOME`、`NEXT_HOOKS_DIR`、`NEXT_SKILL_ROOT` 等环境变量覆盖。

## License

MIT
