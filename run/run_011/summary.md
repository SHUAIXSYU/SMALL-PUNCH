# run_011 — Existing Project GUI registration repair

**PASS（仅限现有 Project 注册与公开 API 回查）。** 官方 `AbqJobPilotClient.register_project()` 返回 `PROJECT_REGISTERED`，随后 `list_projects()` 返回且仅返回一条匹配的 Project 记录。

- 名称：`SP-InvOpt run_008 candidate preview`
- ID：`b87d2cd6-8519-4ac3-bae6-7eb989fb2dae`
- 根目录：`E:\Projects\SMALL-PUNCH\agenthub_sp_invopt\abqjobpilot_project`
- GUI 用户级注册表：`C:\Users\wuxia\.abqjobpilot\recent_projects.json`

根因是 run_008 的 API 使用仓库内独立 `agenthub_sp_invopt/abqjobpilot_recent_projects.json`；创建成功，但未注册到 GUI 的用户级最近列表。实际 GUI 窗口为 Agent Command Console，进程所属用户与 Codex 均为 BOLTZMANN\wuxia。父进程使用归档0.1.0虚拟环境的解释器，子进程使用其Python39基础安装，但两者命令行均指向稳定版 `D:\Projects\abqjobpilot\run_gui.py`，属于同一启动的父子进程。GUI源码以默认 ProjectManager 初始化并把同一 recent_file 传给 Agent Command Console；没有发现不同 Windows 用户或不同应用源码安装。用户级 app_settings.json 不存在，默认 Projects 根目录由源码解析为用户 `.abqjobpilot/projects`，这不限制打开任意合法Project目录。

注册前官方 API 核验 Project manifest ID 完全一致、runtime/queue.json 存在且有效，队列0项。注册后官方 API 最近列表出现匹配名称/ID/根目录。既有5条最近记录全部保留；Project manifest、Queue、live_status、Settings、app_settings、仓库独立recent文件的存在性/哈希均保持。未创建Project、入队、运行Solver、修改Settings/稳定版源码或commit/push。

当前已打开的控制台下拉框可能仍持有旧列表；关闭 **Agent Command Console** 窗口后重新打开，会在初始化时重新读取最近项目。未操作或目视确认GUI刷新，不把API回查当成已看到界面。

本轮新增run_011记录、注册脚本和证据，并更新Run索引与项目状态。主结果见 [registration_result.json](artifacts/registration_result.json)；注册前最近项目快照及API列表保存在忽略的private目录。run_010的真实Settings缺失与Solver准入阻塞仍然有效。完成本轮后停止。
