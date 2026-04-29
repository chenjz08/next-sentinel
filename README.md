# Next Sentinel

Next Sentinel 是一个 macOS 状态栏小工具，用来给 Codex App 的长程任务做一次性兜底。

它监听 Codex App 启动事件，等待 60 秒让 Codex 完成初始化，然后通过 `next_ctl.py trigger` 单次调度 `automation-2`。自动化会恢复目标会话，读取最近一次完成输出里的 `NEXT:` 标识，再把对应的技能引用发回目标会话。执行后 `automation-2` 会回到 `PAUSED`，避免变成每分钟常驻轮询。

## 功能

- 常驻 macOS 状态栏，显示为 `NEXT`。
- 监听 Codex App bundle identifier：`com.openai.codex`。
- Codex 启动或重启后等待 60 秒，再触发一次兜底。
- 支持状态查看、启动 NEXT、停止 NEXT、立即触发兜底、打开日志和打开 hooks 目录。
- 随仓库提供 Codex hook 脚本、安装脚本、配置示例、自动化示例和测试用例。
- 记录 Cockpit Tools 自动切号与 Codex 重启链路，但不提交真实账号或 token。

## 工作流程

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

完整关联见 [docs/usage-associations.md](docs/usage-associations.md)。

## NEXT 协议

目标会话每轮最后需要留下一个明确标识：

```text
NEXT: 继续
NEXT: 实现
NEXT: 修复
NEXT: 审查
NEXT: 发布
NEXT: 停止
```

分发规则：

| 标识 | 发送内容 |
| --- | --- |
| `NEXT: 继续` | 纯文字 `继续` |
| `NEXT: 实现` | `incremental-implementation` 和 `test-driven-development` 两个技能 |
| `NEXT: 修复` | `incremental-implementation` 和 `test-driven-development` 两个技能 |
| `NEXT: 审查` | `code-review-and-quality` 技能 |
| `NEXT: 发布` | `shipping-and-launch` 技能 |
| `NEXT: 停止` | 不发送任何内容 |

路由器会从最近完成输出的底部向上找最后一个独立的 `NEXT:` 标识。下面这种协议说明行不会被当成标识：

```text
NEXT: 继续/实现/修复/审查/发布/停止
```

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

## 安装 hooks

```bash
./scripts/install-hooks.sh
```

脚本会把这三个文件复制到 `~/.codex/hooks/`：

```text
next_ctl.py
next_session_start.py
next_stop_router.py
```

然后按需修改：

```text
~/.codex/hooks/next_router_config.json
~/.codex/config.toml
~/.codex/automations/automation-2/automation.toml
```

示例文件：

```text
examples/next_router_config.example.json
examples/config.toml.snippet
examples/automation-2.toml
```

如果你的 Codex 版本不展开 `~`，把 `examples/config.toml.snippet` 里的 hook 命令改成绝对路径。

检查状态：

```bash
python3 ~/.codex/hooks/next_ctl.py status
```

## 构建 App

环境要求：

- macOS 13 或更新版本。
- Xcode Command Line Tools，用于 `swiftc` 和 `iconutil`。
- Python 3。
- Pillow，用于渲染图标：`python3 -m pip install pillow`。

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

## Cockpit 自动切号与 Codex 重启

Cockpit Tools 是外部工具，本仓库不调用未公开 API，也不保存真实认证内容。

本机链路中，Cockpit Tools 会维护类似下面的状态文件：

```text
~/.codex/.cockpit_codex_auth.json
```

仓库只提供字段示例：

```text
examples/cockpit_codex_auth.example.json
```

切号完成后，重启 Codex：

```bash
./scripts/restart-codex.sh
```

如果 Next Sentinel 已运行，它会监听到 Codex 启动，并在 60 秒后触发一次 `automation-2`。

## 常用命令

```bash
python3 ~/.codex/hooks/next_ctl.py status
python3 ~/.codex/hooks/next_ctl.py start
python3 ~/.codex/hooks/next_ctl.py stop
python3 ~/.codex/hooks/next_ctl.py trigger
```

状态含义：

- `NEXT hooks: ACTIVE`：hook 路由启用。
- `NEXT hooks: STOPPED`：通过 `NEXT_ROUTER_DISABLED` 暂停路由。
- `automation-2 db: PAUSED`：兜底自动化空闲。
- `automation-2 db: ACTIVE`：正在等待本次单次触发执行。

## 测试

测试用例按项目要求放在 `test/` 目录：

```bash
python3 -m unittest discover -s test -p 'test_*.py'
```

测试覆盖：

- `NEXT: 实现` 后面有其他上下文时，仍按 `实现` 路由。
- 多个 `NEXT:` 标识时，使用最后一个明确标识。
- 协议说明行不会被误判为标识。
- `实现` 和 `修复` 会发送两个技能引用，不会降级成 `继续`。
- `automation-2` 单次触发后会回到 `PAUSED`。

## 技能仓库来源与致谢

这套用法基于“技能就是一个本地 Markdown 文件”的约定。我们的本地技能体系里使用了宝玉大神 Jim Liu 的技能仓库：

- 仓库：[jimliu/baoyu-skills](https://github.com/jimliu/baoyu-skills)
- 来源：宝玉技能生态，Jim Liu

Next Sentinel 的核心路由不依赖 `baoyu-*` 技能，但沿用了这种本地技能文件组织方式，也建议和这类技能仓库一起使用。基于本项目继续发布时，请保留这段致谢。

## 安全说明

- 不提交 `~/.codex/.cockpit_codex_auth.json`。
- 不提交 Codex 的 `auth.json`、sqlite 数据库、真实 session 状态和日志。
- `examples/` 里的 session、cwd、账号字段都是占位示例。
- hook 脚本默认读取 `$HOME/.codex`，也支持用 `CODEX_HOME`、`NEXT_HOOKS_DIR`、`NEXT_SKILL_ROOT` 等环境变量覆盖。

## License

MIT
