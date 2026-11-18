# run_031 — 八项授权下的 I01 Queue-only 入队

**I01_QUEUED_AWAITING_MANUAL_START。** 用户明确批准 run_030 冻结的 I01–I08 各最多一次 Datacheck+Full Analysis；此 Run 只将 I01 入队。8项授权不意味着同时运行8项；I02–I08 的 AgentHub 任务处于依赖门控等待状态，用户无须为同一冻结范围再次授权。新入队1项，实际启动尝试确认0项，尚未提交7项，零自动重试。

| 身份 | 当前记录 |
| --- | --- |
| Job | `SPIO_R030_I01_G` |
| queue_id | `q_c8329bd4fab4455f924d211d62ba0625` |
| I01 AgentHub task_id | `3afd05ca-ba91-45cb-9494-67ebc0225ff6` |
| 八项预算 task_id | `39eef014-3f30-4fdb-9c3e-c33fbd810429` |
| Project ID | `b87d2cd6-8519-4ac3-bae6-7eb989fb2dae` |
| INP | `run/run_030/artifacts/candidates/SPIO_R030_I01_G/SPIO_R030_I01_G.inp` |
| INP SHA-256 | `60a9631854792cb0ab61ce48eceff182bcfd5ab12679f8c0a77ac0078c9ac1ea` |
| 独立工作目录 | `run/run_030/artifacts/solver/SPIO_R030_I01_G` |
| 参数 | σy=190.14278543376116 MPa, n=0.44 |
| 资源与阶段 | 14 CPU，0 GPU，Datacheck=True，Full=True；每项最多一次，无自动重试 |

通过本机 AbqJobPilot 0.2.2 公开 API 验证 Project ID、PERSISTED Settings、Abaqus 2024 命令存在、Queue/Runner 无其他可执行或待恢复状态；冻结8份输入和目录哈希/冲突检查通过。I01 Preflight=`PREVIEW_READY`、dry-run=`DRY_RUN_READY`。单次正式 `enqueue_only` 返回上述 queue_id。再次回读 Queue，**只有 I01 可执行且为 QUEUED**，CPU/GPU、两阶段、输入和工作目录与冻结值一致。I02–I08 未入队；I01 工作目录尚无求解输出，Datacheck/Solver 未启动。历史8项 Queue 记录均为终态，未清空或修改。

MAIN通过正式AgentHub身份登记总授权、8个输入完整SHA、8项各自的Queue任务和结果审核任务、I01的任务级入队与手动启动许可，并记录 I01 queue_id。I02 依赖 I01 的真实结果经MAIN审核；I05 另依赖 I01–I04 阶段关口。Hub本身不会自动唤醒其他 Codex 会话，也不启动 Runner。预算状态见[结构化台账](artifacts/budget_status.json)，完整检查见[准入证据](artifacts/admission.json)、[Queue回读](artifacts/queue_after.json)与[提交结果](artifacts/enqueue_result.json)。

**人工停止点：**请在 AbqJobPilot GUI 打开 `E:\Projects\SMALL-PUNCH\agenthub_sp_invopt\abqjobpilot_project`，确认只有 `SPIO_R030_I01_G` 待执行，然后由您点击一次 **Start Queue**。当前公开接口未替您启动 Solver。完成后需重新激活 MAIN，以公开历史和真实输出核验，交真实 ODB Agent 只读提取并做冻结 Loss/数值审核；通过后方可在本次8项授权内提交 I02。失败或身份不明时暂停，不能重新入队或补跑。run_025 历史 BLOCKED 与保留拉伸禁读规则不变。
