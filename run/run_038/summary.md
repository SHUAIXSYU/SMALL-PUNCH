# run_038 — D09 第二次独立重试入队

**WARNING / D09_RETRY2_QUEUED_AWAITING_MANUAL_START。** 用户通过 GUI 的官方恢复将上次重试 `q_ed246bd7469b4701a8570326dfb73eb3` 标为 UNKNOWN_INTERRUPTED，并从 Queue 移除其记录；Project History 中该尝试仍保留 UNKNOWN。Live 已为 IDLE，无正在运行的 Solver，当前 Queue在提交前没有可执行任务。原始 D09 的旧锁文件保留于原输出目录。

唯一新 Job `SPIO_R038_D09_RETRY2` / `q_434c5f15c837413f8628b5b5188088aa` 使用原冻结 INP `E:\Projects\SMALL-PUNCH\run\run_033\artifacts\candidates\SPIO_R033_D09_L\SPIO_R033_D09_L.inp`，SHA-256 `5d754294edca19e8eef85661f5a99f18cfe189f484b86ddb5e3ee52acc354d4b`；独立空工作目录 `E:\Projects\SMALL-PUNCH\run\run_038\artifacts\solver\SPIO_R038_D09_RETRY2`。数值与 Loss 契约不变，14 CPU、0 GPU、Datacheck+Full，零自动重试。公开 API Preflight=PREVIEW_READY，Dry-run=DRY_RUN_READY，queue-only 入队后仅此 Job 为 QUEUED；Codex 未启动 Datacheck 或 Solver。

请在 Project ID `b87d2cd6-8519-4ac3-bae6-7eb989fb2dae` 对应的 GUI 中确认只显示该待执行 Job，再由您点击一次 Start Queue。求解成功、数值有效和实验拟合均尚未评估。旧 run_034、run_036/037 历史结论不改写。

AgentHub task `134d96cb-6ea2-43ed-87c7-6f74fbf2ebd7`；预检与授权见 `artifacts/private/precheck.json`、`artifacts/authorization_scope.json`，真实 Queue 收据见 `artifacts/queue_receipt.json`。
