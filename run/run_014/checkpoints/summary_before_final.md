# run_014 — First authorised Hollomon forward validation

**RUNNING（结果交接中）：Datacheck PASS；Full Analysis COMPLETED_WITH_WARNINGS，返回码0。正在等待真实 ODB Agent 提取与诊断。**

Full Analysis于22:16:33结束，AbqJobPilot两阶段总耗时165秒，STA正常完成；独立工作目录已生成ODB/STA/MSG/DAT/LOG，原位记录哈希。MAIN已登记终态证据任务 `21e7ccb4-7061-4cdb-ad73-9506ee7c424d` 并创建正式 ODB 任务 `35b07ba1-22ad-48a7-b859-2d99199ed419`，通过 Codex 消息工具通知既有真实 `SP-InvOpt ODB` 会话；发送成功不等于已领取，须继续核实Hub租约和结果。见 [终态证据](artifacts/solver_terminal_result.json)、[ODB交接](artifacts/odb_handoff.json)。

进程审计保留 WARNING：Full阶段有一个短暂PID14320在身份采集前已经消失，native聚合复核仍为UNCONFIRMED。所有完整身份的launcher/pre.exe/standard.exe等均确认退出；当前PID列表中14320不存在，Runner ABSENT/IDLE、无.lck，五项输出哈希期间及2秒间隔均稳定，独立确认的是“当前可只读”，不声称完整历史进程链已验证。未修改外部状态或源码。终态收集脚本首次误用活动live字段、第二次因上述审计限制停止；诊断与两个脚本快照保留，修正仅涉及本Run证据收集，没有Solver重试。

此前22:14:42+08:00 只读快照确认同一 queue_id 的 Datacheck 返回码 0，Runner 于22:14:25进入 Full Analysis。下述运行中及入队快照保留阶段事实，最新状态以上方终态为准。[运行中快照](checkpoints/observation_20261021T221442948563.json)。

## 身份及授权

- AgentHub task_id：`93322987-9489-47c1-908a-dd43e0736339`。
- AbqJobPilot queue_id：`q_4c0358a918a7447d807d2f547d22c7b8`。
- Job：`SPIO_R014_Q200_N010`；Project：`b87d2cd6-8519-4ac3-bae6-7eb989fb2dae`。
- 唯一输入：[run_008 候选 INP](../run_008/artifacts/candidate_inp/SPIO_R008_Q200_N010_Candidate/SPIO_R008_Q200_N010_Candidate.inp)。SHA-256：`fa2de5d73a28536c1c07cd22072d2a24c1ae988c569127d728931c583457f05a`。
- 独立输出目录：`run/run_014/artifacts/solver/SPIO_R014_Q200_N010`。该位置遵从本轮用户明确指定路径；solver 子目录单独忽略，原始输入未复制或修改。
- 参数：sigma_y=200 MPa、n=0.1、E=210000 MPa、nu=0.3、max_plastic_strain=0.9。14 CPU、0 GPU、Datacheck=true、Full Analysis=true；最多一个 Job、一次尝试、零自动重试。

用户在本轮消息明确授权本次入队及通过 GUI Runner 执行。MAIN 将完整、不可扩展的范围存入现有 Hub 任务 payload，分别登记 enqueue 和 start_solver approval，没有 recover_retry approval。Hub 的历史外部执行器仍禁用；它仅记录授权、消息和证据，实际队列操作由 MAIN 使用 AbqJobPilot 公开 enqueue-only API 完成，没有更改 Hub 权限实现。

## 已执行检查

新编号经索引和目录核对后独占创建。基线 main / e87aadc9f7074fc4bc127c9ae03afbe9081dabae；用户既有修改保留。解释器为已登记的 `D:\XianLab\envs\torch-gpu\python.exe`，Python 3.11.13，SQLite 3.50.2；协调仅用标准库与已有本地模块。

1. 严格 ID 查询确认专用 Project 和 Runtime；Settings=PERSISTED，defaulted_fields=[]，磁盘值与 API/effective_settings 完全一致。
2. Abaqus 命令 `D:\ABAQUS2024\Commands\abq2024.bat` 存在，CPU/GPU/两阶段均符合授权，Auto shutdown=false。
3. 输入哈希与 run_013 完全一致；全部有效关键字检查没有 INCLUDE、IMPORT、FILE/INPUT/LIBRARY/OLDJOB 引用或 RESTART READ，只有 RESTART WRITE。工作目录变化无需外部输入复制。
4. 当前修复版 AbqJobPilot 0.2.2 / 7012133e7cc0176bb3e56fc24d7154ee3b90bb81，外部工作树干净。新 Job 名和工作目录的 preflight=PREVIEW_READY、dry-run=DRY_RUN_READY。
5. 入队前 Queue 为空、历史无本 Job、Runner ownership=ABSENT、live phase=IDLE、无未解决过程证据或报告。OS 进程扫描未发现活动 Solver/目标路径冲突，新工作目录为空。现存 `.queue.lock` 未删除或修复。
6. 原生队列事务内再次检查空队列和输入/配置，再调用公开 `enqueue(request, dry_run=False)` 一次；显式 submission_mode=enqueue_only、allow_solver_submit=false。返回 ENQUEUED，solver_started=false、runner_started=false。回读 Queue 恰有一条本 Job，全部字段符合授权。
7. 原始候选、CAE、Project manifest、Settings、用户 recent/app_settings、run_013 JSON 证据等保护文件哈希保持；没有修改外部源码、安装环境或直接写 Queue/Project DB/Hub DB。

检查与实际 API 响应见 [admission](artifacts/admission.json)、[入队前复核](artifacts/admission_before_enqueue.json)、[request](artifacts/request.json)、[enqueue response](artifacts/enqueue_response.json)、[queue snapshot](artifacts/queue_after_enqueue.json)。

## 唯一执行及恢复边界

`checkpoints/enqueue_attempt.json` 在实际 API 调用前独占写入。脚本遇到该标记立即停止，不能重新入队；即使调用返回不明也只允许人工检查 queue_id。现有 Queue 身份及历史还会阻止重复准备。没有自动重试路径，未调用 Runner/命令启动器。

已审阅当前 Runner：使用队列显式 job_name、inp_path、work_dir；Datacheck 非 PASS 即终止该 Job；成功才进入同一 Job 的 Full Analysis；循环仅领取 QUEUED/DATACHECK_OK，不自动重试失败 Job。这是源码检查，不是对本次计算阶段的成功断言。

Hub 已登记九项新证据及 SHA-256，MAIN 完成消息已回读、审计链通过。该 Hub 协调任务的 COMPLETED 仅表示授权登记和入队完成，科学状态 NOT_EVALUATED。[AgentHub 回执](artifacts/agenthub_receipt.json)。

## 入队时结果与后续流程

最新入队快照时间见 [enqueue_result](artifacts/enqueue_result.json)。Datacheck=NOT_STARTED；Full Analysis=NOT_STARTED；duration=null；ODB 未生成、有效性未评估。输出定位 API 仅返回预期位置，不构成产物存在证明。ODB Agent 尚未派单，须等 Full Analysis 真实结束及安全读取条件满足后才创建正式任务。没有本次 F–D 曲线或新的数值警告可报告，与 Sanity Job-1 的求解差异目前 UNKNOWN；材料差异可引用 run_007/008/010 的静态证据，不能虚构求解比较。

请用户在修复版 GUI 打开 `agenthub_sp_invopt/abqjobpilot_project`，确认队列只有本 Job 后点击一次 **Start Queue**。公开 API 不支持 Solver Start，MAIN 不使用 subprocess、Abaqus CLI 或 GUI 自动化代替。当前授权已覆盖同一 Job 的两阶段，无须重复申请；任何失败均保留证据并停止，不重试/重新入队，额外求解须另行授权。

后续仅查询真实状态及日志。Full Analysis 成功且 ODB 安全可读后，按用户授权交给真实 ODB 会话核验身份、提取 Punch RP U2/RF2、生成 F–D CSV/曲线、检查收敛/PEEQ/警告并与历史真实 Job-1 数据比较。候选模型仍为真总应变解释，未获实验验证。本次未 commit/push、未训练、未修改几何/网格/接触/BC/材料参数。
