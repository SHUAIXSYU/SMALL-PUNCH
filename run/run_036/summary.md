# run_036 — D09 第二次尝试的中断诊断

**BLOCKED_RECOVERY_REQUIRED。** 用户要求再次重启 D09，并报告此前 GUI 点错。公开 Queue 记录显示 run_035 的 `SPIO_R035_D09_RETRY1`（`q_ed246bd7469b4701a8570326dfb73eb3`）已于 `2026-10-25T19:13:53` 开始 Datacheck；当前仍为 `DATACHECK_RUNNING`，Live phase=`DATACHECK_RUNNING`，Full Analysis 未有可信完成证据。原始 D09 `UNKNOWN_INTERRUPTED` 状态和旧锁文件继续保留。

AbqJobPilot 0.2.2 稳定版的**只读**恢复评估：owner=`STALE`，solver probe=`CLEAR`，can_apply=`False`。阻塞项：Tracked launcher/solver exit is not established: UNCONFIRMED; A solver .lck file exists; never remove it automatically; No exact queue/live identity, start time, phase and command-exit evidence match; No supported metadata-only transition; manual investigation is required。当前状态为 `STALE_RUNNING`，公开 enqueue 会因 `RECOVERY_REQUIRED` 拒绝；本 Run 未调用任何 enqueue、Solver、Datacheck、恢复写入或清理锁文件。ODB 存在不能说明 Full Analysis 成功。

本机当前/此前 GUI 进程来自 `D:\Projects\abqjobpilot_dev`（源版本0.3.0.dev0），而已验收的公开 API 来源是 `D:\Projects\abqjobpilot` 稳定版0.2.2。稳定版文档明确：恢复修正是**本地 GUI 人工确认**，没有公开 API/CLI/MCP 的 unattended apply。其只读计划目前不可执行，不能由 Codex 绕过或直接修改 Queue JSON、Project DB、Live 状态与锁文件。

下一步需先由用户核实 GUI 操作及 Windows/Runner 状态，并在同一正确 Project 中完成官方恢复评估；当前因缺少命令退出证据且仍有旧 `.lck`，即使打开恢复对话框也可能显示不可应用。若用户选择重新启动 Windows，须确认没有重要未保存工作；之后再用稳定版 GUI 重新评估，不能预先保证准入。只有官方恢复状态明确、Queue 无其他可执行任务、原 INP 哈希和新工作目录检查通过时，才可按新授权创建独立第三次尝试。不能复用 run_035 工作目录，也不能覆盖两次历史产物。

AgentHub task `e6f2c47a-ae0d-470f-95ff-7efe4406fe49` 已记录诊断。盲测隔离与 run_034/035 的历史证据不变。
