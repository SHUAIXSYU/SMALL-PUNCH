# run_052 — H01/H02授权入队

**WARNING / TWO_HARDENING_JOBS_QUEUED_AWAITING_MANUAL_START。** 第一阶段完成：恰好两项本批获授权Job可执行，均QUEUED；无Solver/Datacheck启动，实际FE尝试消耗0。请用户在正确Project核对两项后手动点击一次Start Queue。

Project：`E:\Projects\SMALL-PUNCH\agenthub_sp_invopt\abqjobpilot_project`；ID `b87d2cd6-8519-4ac3-bae6-7eb989fb2dae`。

| 顺序 | Job | queue_id | 当前状态 |
|---|---|---|---|
| 1 | SPIO_R051_H01_LOW | `q_02e7827a5c2d41aba1781ec0f36e78a4` | QUEUED |
| 2 | SPIO_R051_H02_HIGH | `q_5a027a0d764148c08f4d7be36049439f` | QUEUED |

14 CPU、0 GPU，每Job最多一次Datacheck成功后一次Full Analysis，零自动重试，单Runner串行，仅用户GUI启动。AUTO_STOP_UNAVAILABLE已按当前本机Runner源码重新核实，用户接受第一项失败/警告后仍可能继续第二项。

严格PERSISTED Settings、Abaqus命令路径、两份冻结完整哈希、82行材料表、低段和块外字节、最大增量.00125及Punch U2/RF2不变均通过核验。当前Runner CLEAN/IDLE、无活动所有权或待恢复状态，输出目录为空；2/2新Preflight与2/2新Dry-run通过后才顺序入队。只使用公开API，没有直接编辑Queue/Project DB/Hub SQLite、清理锁或修改历史输入。

授权/queue_id/输入与工作目录证据登记AgentHub。[授权](artifacts/private/authorization_scope.json)、[预检查](artifacts/private/precheck.json)、[队列清单](artifacts/private/queue_manifest.json)、[最终回读](artifacts/private/final_readback.json)、[预算台账](artifacts/private/budget_ledger.json)。未来两项ODB只读任务已登记，依赖尚未完成的MAIN执行审核任务，不会因为登记自动唤醒或执行。

未读取拉伸实验，run046冻结预测及run047/048历史保持；没有新输入、拟合、BO/DE/RL或Git提交。第二阶段尚未执行，不存在新F–D/Loss/PEEQ或科学结论。当前停止，等待用户手动计算完成后通知。
