# run_035 — D09 崩溃后的唯一新尝试入队

**WARNING / D09_RETRY_QUEUED_AWAITING_MANUAL_START。** 用户报告电脑死机导致 D09 未完成，并明确批准新增一次同参数重试、由本人在 GUI 点击 Start Queue。原 Job `SPIO_R033_D09_L` / `q_0bebaa417158409fba973efcbae921fd` 仍为 UNKNOWN_INTERRUPTED，原 `.lck`、ODB 和其他产物均未改动。

新 Job `SPIO_R035_D09_RETRY1` / `q_ed246bd7469b4701a8570326dfb73eb3` 已通过 AbqJobPilot 0.2.2 公开 API 单项 queue-only 入队；当前唯一可执行 Queue 记录就是它。直接复用冻结 INP，SHA-256 `5d754294edca19e8eef85661f5a99f18cfe189f484b86ddb5e3ee52acc354d4b`；无新 INP 或本构修改。独立工作目录 `E:\Projects\SMALL-PUNCH\run\run_035\artifacts\solver\SPIO_R035_D09_RETRY1`，14 CPU、0 GPU、Datacheck=True、Full=True、零自动重试。Preflight=`PREVIEW_READY`，Dry-run=`DRY_RUN_READY`。入队后工作目录为空，Solver/Datacheck 未启动。

请在正确的 AbqJobPilot Project（ID `b87d2cd6-8519-4ac3-bae6-7eb989fb2dae`，根目录 `E:\Projects\SMALL-PUNCH\agenthub_sp_invopt\abqjobpilot_project`）中确认 Queue 只显示这个可执行 Job，再由您点击一次 **Start Queue**。当前桌面可见 `D:\Projects\abqjobpilot_dev\run_gui.py` 进程；仅凭进程名不能确认 GUI 已打开本 Project，因此务必核对 Project ID。Codex 未代为启动 GUI Runner。

正式授权和检查证据：`artifacts/authorization_scope.json`、`artifacts/private/precheck.json`、`artifacts/queue_receipt.json`。AgentHub task `8efcd293-a3c6-4a05-bbb8-9e7d47d2bf62` 已登记。旧 run_034 中 D09 Loss=null 与历史状态保留，不能将本次入队视为求解完成。
