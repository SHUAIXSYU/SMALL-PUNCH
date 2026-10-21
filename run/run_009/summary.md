# run_009 — SP-InvOpt AgentHub Runtime 补全与共享 SQLite 验收

**状态：WARNING。** 本轮在已完成的 Run 008 独立 AgentHub 上补全 JSON CLI、AGENTHUB 维护身份、产物版本、失败诊断及任务持有者权限，保留原 `agenthub_sp_invopt/runtime/sp_invopt.sqlite3`。软件验收通过；自动跨 Codex 会话唤醒、真实 AbqJobPilot Settings 与物理求解仍未验证。

## 起始状态与复用审计

- 起始 Git 为 `main` / `e87aadc9f7074fc4bc127c9ae03afbe9081dabae`，remote 为 SMALL-PUNCH `origin`。工作区已有 CAE 修改、REC 删除、run_007、run_008 和共享文档改动；均保留。本 Run 未 commit/push。
- 已读仓库 AGENTS、Run 协议、状态及最近 Run。Run 008 与本 Run 同时进行时，对其目录先只读审计；它完成后才激活兼容迁移。没有覆盖其候选 INP、测试、报告或 SQLite 任务。
- Stage-5 `E:/Projects/Stage-5/RL-LAM-AgentHub` 已实现标准库 SQLite `BEGIN IMMEDIATE` 领取、租约、依赖、幂等、消息、审计链；另有受政策约束的 Codex 会话提醒流程。其提醒策略依赖 Stage-5 的会话绑定与持续授权，不能自动套用到 SMALL-PUNCH。只读审计，没有复制其源码、修改生产台账或运行 Stage-5 测试。
- 本地稳定版 `D:/Projects/abqjobpilot` 为 v0.2.2 / `0dfdb222`。本 Run 实际运行公共 CLI `capabilities --json`，确认 Project、preflight、enqueue、list/status/locate 等接口且无公共 Solver-start；Run 008 另已真实核验五个只读/预览 MCP 工具。没有直接写其 Queue JSON、project.db 或源码。
- Python 按环境登记使用 `D:/XianLab/envs/torch-gpu/python.exe`（3.11.13，SQLite 3.50.2），仅用标准库；未安装或修改依赖。

## Runtime 交付

- [Hub API](../../agenthub_sp_invopt/hub.py) 沿用原 SQLite 台账，新增 `AGENTHUB` 维护身份（独立维护会话表，无科研任务权限）、显式产物 `version`、`failures` 诊断表与 `Hub.fail()/diagnostics()`。旧任务、消息、产物和事件均保留。
- 任务幂等键现在连依赖集合一同比较；消息幂等键不能改发送者或收件角色。产物登记与任务消息要求该任务的创建者或实际租约持有者；同角色的另一 Agent 被拒绝。过期租约恢复仍需 MAIN 的 `recover_retry` 授权和 worker 已停止确认。
- [JSON CLI](../../agenthub_sp_invopt/cli.py) 暴露注册、建任务、批准、inbox、消息、领取、心跳、产物、完成、失败诊断、恢复及审计。可复制用法和 MAIN/AGENTHUB/CAE/ODB 接入说明见 [CLI 指南](../../agenthub_sp_invopt/CLI.md)。消息体和任务体不作为命令执行。
- `AGENTHUB` 为维护角色：可注册和留下会话审计，不能创建、批准、领取或完成科研任务。MAIN、CAE、ODB 的科研职责保持 Run 008 协议。该设计将系统维护与科研授权分开。

## 实际验收

- [独立进程 CLI 交接](artifacts/cli_acceptance.log) 使用同一持久 SQLite：MAIN 建 CAE 任务并发送消息 → CAE 领取、写入 `SIMULATED_ONLY.inp.txt`、登记 SHA-256 后完成 → ODB 领取依赖任务、读取模拟证据并提交模拟结果 → MAIN 收到持久消息。两个任务分别为 `2633f7d0-78c0-40f0-8a7d-d72967b510b7` 和 `22da6859-21e1-4761-842d-e58f12549565`；[机器报告](artifacts/private/cli_acceptance_report.json) 与 SQLite 留在忽略私有区。该文件不是 Abaqus INP，所有结果明确标为 `SIMULATED_ONLY` / `NOT_EVALUATED`。
- 同一交接检查重复任务、重复消息、每会话一次收件、错误角色领取、重复领取、重复完成拒绝、依赖、产物哈希和审计链。Run 008 的 [8 项原测试回归](artifacts/reuse_regression_final.log) 全通过，其中有并发双会话单赢家和租约过期恢复。新增 [8 项定向测试](artifacts/extensions_final.log) 全通过，覆盖版本冲突、失败诊断与 CLI 回读、依赖幂等、AGENTHUB 越权拒绝、同角色非持有者拒绝、消息改路由拒绝和恢复授权。
- 首次定向测试发现版本、失败诊断和依赖幂等三个缺口，原始失败保留在 [修复前日志](artifacts/extensions_before.log)，未当作通过。修复后通过。
- 对 Run 008 台账先做 SQLite 备份，再在原路径执行增量迁移。[激活报告](artifacts/activation_report.json) 记录迁移前后均为 3 个任务、6 个产物、12 条消息、39 条事件；SQLite `integrity_check=ok`，旧审计链有效。原始备份位于忽略私有区，SHA-256 为 `c1db06bca2e8e9da1cbb6383e93ee53152547a3e71633509868eb57c1aa498af`。迁移后 AGENTHUB 维护会话登记成功，审计链再次通过。

## 边界与未验证项

- 当前 Codex 平台提供对现有 chat 发送消息的工具能力，Stage-5 有受授权的提醒流程；本 Hub 没有后台唤醒器、会话绑定或对 MAIN/CAE/ODB Codex chat 的自动投递。数据库 Inbox 和独立本地进程收到消息，**不等于另一 Codex 会话已被唤醒或领取**。本 Run 没有向其他会话发送消息；继续使用显式人工 Handoff 和主动轮询。
- 当前接口面向同一受信任本机工作区的协作进程。SQLite 文件和 session ID 对拥有文件访问权的进程不构成强认证；不能把角色拒绝测试解释成对恶意本机进程的安全隔离。
- 旧 Run 008 产物在新增 `version` 字段中使用兼容迁移默认值 `1`，其原始文件语义版本仍以各自 provenance/Run 008 记录为准。新产物应显式传 `--version`。任务结果 `COMPLETED` 只表示执行完成；科学状态仍是 `NOT_EVALUATED` 或 `WARNING`。
- 没有运行 Abaqus Solver/datacheck、入队、训练 RL、优化或生成真实新 ODB。AbqJobPilot Settings 仍缺失；preflight/dry-run 与物理结果均未本轮验证。没有更改原始 CAE/ODB、Stage-5、AbqJobPilot 或其他外部项目。

Run 009 到此结束，等待下一条指令。
