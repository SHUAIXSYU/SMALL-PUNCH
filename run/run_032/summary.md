# run_032 — I01真实结果与I02受控入队

**WARNING / I02_QUEUED_AWAITING_MANUAL_START。** 用户GUI启动的I01经AbqJobPilot公开接口确认Datacheck与Full均返回0，Queue为`COMPLETED_WITH_WARNINGS`，唯一执行尝试、输入哈希与ODB/STA/MSG/DAT/LOG身份吻合；Runner总耗时210秒。真实ODB Codex会话通过AgentHub任务`9225daaf-c253-44b7-bbd8-f574bbf6ce38`领取、只读提取并回传，MAIN任务`bf1d6521-6052-4890-95e8-2b955896985c`独立复核后按求解前冻结的run_030门槛批准仅I02继续。审批只表示探索性数值评价可继续，不代表材料物理验证。

I01 Punch RP正向F–D有403帧，完整覆盖0–1.2 mm；原339点实验曲线中冻结241点、等权、固定1428.9 N、不外推的`run017-exploratory-fd-v1`得探索性PROVISIONAL Loss **1.954386320143**，RMSE **1997.593 N**、NRMSE **1.397994**。最大保存帧PEEQ **0.524459**，低于0.85人工裕度检查线及0.9材料表终点。STA为402接受增量、0拒绝试算、0 cutback；未见接受态负特征值、过度畸变或大应变警告。接受态首增量零力矩提示和DAT接触跟踪回退提示保留为WARNING；接触/局部F–D未发现未解释的明显突跳。历史Runner进程证据仍为UNCONFIRMED，当前只读安全与真实终态由独立证据核对，不能据此追认历史进程细节。

I02 `SPIO_R030_I02_L` 在既有8次冻结授权内通过哈希、Project/PERSISTED Settings、Runner/Queue、工作目录、Preflight及dry-run复查后，**仅通过公开API入队一次**。queue_id=`q_a40ddbf45cec472cb3541e28e6184fad`，INP SHA-256=`c93d77fcbd6e0bab8a12e439a3ab987a37360663296d6e2e62ceaa2610814e47`，工作目录=`E:\Projects\SMALL-PUNCH\run\run_030\artifacts\solver\SPIO_R030_I02_L`，14 CPU/0 GPU，Datacheck和Full启用、零自动重试。当前唯一可执行Queue记录是I02，未启动Datacheck/Solver；I03–I08未入队。用户应在正确Project中确认只有I02待执行，手动点击一次Start Queue。AbqJobPilot无可靠自动异常停队列；本次单Job方式保持逐项审核。

AgentHub保留授权、I01 ODB真实会话消息与证据、MAIN准入决定、I02入队审批和Queue回读。私有曲线/原始可恢复实验数据位于本Run的Git忽略目录`artifacts/private/odb/`；证据含完整哈希清单。封存拉伸验证资料未读取，历史信息暴露声明和run_025原BLOCKED结论保持。无Codex启动求解、重试、改冻结INP、DE/BO/RL或Git提交。

关键证据：`artifacts/private/execution_audit.json`、`artifacts/private/odb/REPORT.md`、`artifacts/private/odb/result.json`、`artifacts/private/odb/manifest.json`、`artifacts/main_i01_gate.json`、`artifacts/i02_admission.json`、`artifacts/i02_enqueue_result.json`、`artifacts/budget_status.json`。
