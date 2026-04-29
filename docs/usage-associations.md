# 使用关联总览

Next Sentinel 不是单独的自动化引擎，它负责把 Codex App、Codex hooks、`automation-2`、本地技能文件和可选的 Cockpit Tools 切号流程串起来。

## 关联对象

| 对象 | 默认位置或标识 | 作用 |
| --- | --- | --- |
| Codex App | `com.openai.codex` | Next Sentinel 监听它的启动事件。 |
| Next Sentinel App | `~/Applications/Next Sentinel.app` | 状态栏工具；Codex 启动后延迟触发一次兜底。 |
| 控制脚本 | `~/.codex/hooks/next_ctl.py` | 启停 hooks、查询状态、单次调度 `automation-2`。 |
| SessionStart hook | `~/.codex/hooks/next_session_start.py` | 会话启动/恢复时注入 NEXT 协议。 |
| Stop hook | `~/.codex/hooks/next_stop_router.py` | 读取最后一个明确 `NEXT:` 标识并分发下一步。 |
| 路由配置 | `~/.codex/hooks/next_router_config.json` | 绑定目标 session、目标 cwd、技能根目录和最大自动续跑次数。 |
| 兜底自动化 | `~/.codex/automations/automation-2/automation.toml` | Codex 重启后由 Next Sentinel 单次触发。 |
| 自动化数据库 | `~/.codex/sqlite/codex-dev.db` | `next_ctl.py` 同步更新 `automation-2` 的 `status` 和 `next_run_at`。 |
| 技能目录 | `~/.codex/skills` | Stop hook 发送本地 `SKILL.md` Markdown 引用。 |
| Cockpit Tools | `com.jlcodes.cockpit-tools` | 可选：用于 Codex 账号切换。真实认证文件不进入仓库。 |
| Cockpit 认证状态 | `~/.codex/.cockpit_codex_auth.json` | 可选：由 Cockpit Tools 写入，包含账号标识和认证状态；只能本机保留。 |

## NEXT 标识到技能的映射

| 标识 | 分发内容 |
| --- | --- |
| `NEXT: 继续` | 纯文字 `继续` |
| `NEXT: 实现` | `incremental-implementation`、`test-driven-development` |
| `NEXT: 修复` | `incremental-implementation`、`test-driven-development` |
| `NEXT: 审查` | `code-review-and-quality` |
| `NEXT: 发布` | `shipping-and-launch` |
| `NEXT: 停止` | 不发送任何内容，并重置该 session 的续跑计数 |

Stop hook 会从最近完成输出的底部向上找最后一个独立的 `NEXT:` 标识。`NEXT: 继续/实现/修复/审查/发布/停止` 这种协议说明行不会被当成实际标识。

## Codex 重启后的自动化链路

```text
Cockpit Tools 切换 Codex 账号（可选）
      |
      v
重启 Codex App
      |
      v
Next Sentinel 监听到 com.openai.codex 启动
      |
      v
等待 60 秒，给 Codex 初始化和账号状态加载留时间
      |
      v
next_ctl.py trigger 把 automation-2 调度到当前时间
      |
      v
automation-2 恢复目标会话，读取最近输出里的 NEXT 标识
      |
      v
目标会话仍运行：不发消息
目标会话可继续：按 NEXT 映射发送文字或技能引用
      |
      v
next_ctl.py 后台 watcher 把 automation-2 改回 PAUSED
```

## Cockpit 自动切号边界

本仓库只保留 Cockpit 与 Codex 重启链路的关联说明，不包含真实账号、token 或 Cockpit 私有接口。

安全边界：

- 不提交 `~/.codex/.cockpit_codex_auth.json`。
- 不在脚本里伪造 Cockpit Tools 的未公开 API。
- 切号完成后通过 `scripts/restart-codex.sh` 重启 Codex，让 Codex 重新读取账号状态。
- Next Sentinel 只监听 Codex 启动并触发兜底，不接管 Cockpit 登录逻辑。
