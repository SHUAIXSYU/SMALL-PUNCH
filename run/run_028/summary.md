# run_028 — 单项授权 Queue-only 入队

**SPIO_R027_CTR_M0025_QUEUED_AWAITING_MANUAL_START。** 本 Run 仅处理用户新授权的一个候选。入队时间记录：2026-10-24T17:30:50.456820+08:00。Datacheck、Full Analysis 和数值资格均未开始或评价。

| 身份 | 值 |
| --- | --- |
| Job | `SPIO_R027_CTR_M0025` |
| queue_id | `q_6919f51c551844b4bcda1cc22b9a6bc4` |
| AgentHub MAIN task_id | `1434ef26-a98f-45ed-8289-891d86b29241` |
| Project ID | `b87d2cd6-8519-4ac3-bae6-7eb989fb2dae` |
| INP | `run/run_027/artifacts/candidates/SPIO_R027_CTR_M0025/SPIO_R027_CTR_M0025.inp` |
| INP SHA-256 | `dae9345bc60973c27edec498dfbd27f269e1f5bbe151316918862954faac40c9` |
| 工作目录 | `run/run_027/artifacts/solver/SPIO_R027_CTR_M0025` |
| CPU / GPU | 14 / 0 |
| 模式与次数 | 单次 Datacheck 成功后单次 Full Analysis；零自动重试 |

## 入队前核验

依实际 `AGENTS.md`、Run 协议、盲反演协议和 AgentHub 契约创建独立 run_028。已记录 Git branch、HEAD、remote、初始工作树及绝对 Torch-GPU Python 解释器；保留原有用户改动，未 commit/push。源是 run_027 冻结候选，不重生成 INP；完整 SHA 与用户授权一致、逐字节与 V01 的唯一允许变化一致。冻结工作目录原先为空，入队后仍无输出。

本机 AbqJobPilot 0.2.2 公开接口确认 Project ID 与目录，Settings=`PERSISTED`，Abaqus 2024 命令真实存在，14 CPU/0 GPU、Datacheck/Full开启。Runner owner=`ABSENT`、live=`IDLE`、recovery=`CLEAN`，无锁或相关活跃进程。入队前其余七项均是历史终态，没有其他可执行 Queue 记录，也无本候选历史尝试或同名 Queue 记录。Preflight=`PREVIEW_READY`、Dry-run=`DRY_RUN_READY`；预览未改变 Queue。

MAIN 使用 AgentHub 正式接口建立任务并绑定用户授权，任务级批准 `enqueue`；随后在 AbqJobPilot 正式运行时事务内通过公开 API 一次 `enqueue_only`，`allow_solver_submit=False`。真实回读确认只有本候选可执行且状态为 `QUEUED`，输入、SHA、资源、阶段及工作目录一致；原有七项历史终态保留。已保存不可自动重试的调用尝试记录和 queue_id，并在 AgentHub 登记证据、核验审计链。

## 人工停止点

请在修复版 AbqJobPilot GUI 打开 Project `b87d2cd6-8519-4ac3-bae6-7eb989fb2dae` 对应目录，确认只有 `SPIO_R027_CTR_M0025` 待执行，然后由用户本人点击一次 **Start Queue**。Codex 未启动 Runner、Datacheck 或 Solver。GUI 启动后的真实状态必须待用户通知并通过公开历史和真实输出重新核验；入队不代表计算完成或数值资格通过。V02 未入队，其原条件授权未使用或转移。

后续仅在真实计算结束后按 `run027-adjacent-refinement-v1` 冻结契约做只读 ODB 提取与比较；run_025 原 `BLOCKED_V01_NUMERICAL_QUALIFICATION` 结论保留。无新计算、参数搜索或封存拉伸数据访问授权。

审计文件：`artifacts/admission.json`、`artifacts/authorization.json`、`artifacts/request.json`、`artifacts/enqueue_response.json`、`artifacts/queue_after.json`、`artifacts/postcheck.json`、`artifacts/enqueue_result.json`、`artifacts/agenthub_receipt.json`、`checkpoints/enqueue_attempt.json`。
