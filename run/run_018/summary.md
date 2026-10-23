# run_018 — P01 Queue-only Submission

## 结果

**PASS，仅限唯一 P01 入队与证据登记。执行状态：QUEUED / AWAITING_GUI_START。**

- task_id：`37ad24d5-26af-4374-b415-c6a1af1fc0c7`
- queue_id：`q_bdec6a60a31849d0a2afe200a70231bd`
- Job：`SPIO_R017_P01_CTR`
- INP：[冻结 P01](../run_017/artifacts/candidates/SPIO_R017_P01_CTR/SPIO_R017_P01_CTR.inp)
- SHA-256：`3a97ee2a121261515a2c4019fbd0e1fedf1391ff5a988021786673c592892576`
- 参数：sigma_y=387.2983346207417 MPa、n=0.26、E=210 GPa、nu=0.3，候选真总应变 Hollomon 契约。
- 工作目录：`run/run_017/artifacts/solver/SPIO_R017_P01_CTR`（仓库相对路径）。
- CPU=14、GPU=0；Datacheck=True、Full Analysis=True；自动重试=0。

## 实际动作与核验

读取实际 Run/AgentHub 协议、冻结清单和环境登记；使用绝对 torch-gpu 解释器 Python 3.11.13。新建 run_018，保留已有 Git 改动及历史 Run。

正式 Project ID `b87d2cd6-8519-4ac3-bae6-7eb989fb2dae` 完全匹配。修复版 AbqJobPilot 0.2.2 公开 API 返回 Settings=PERSISTED，无默认值回退。命令文件 `D:\ABAQUS2024\Commands\abq2024.bat` 存在；14 CPU、GPU关闭、Datacheck/Full开启、自动关机关闭均与保存文件一致。

完整 INP/参数哈希通过，未重新生成或修改。未发现相对 INCLUDE/import 等外部输入依赖，工作目录为空。Preflight=PREVIEW_READY、Dry-run=DRY_RUN_READY；Runner ownership=ABSENT、live phase=IDLE，无冲突求解进程。预览不证明 Abaqus 语法、许可证或收敛有效。

通过公开 API 显式传入 Project、INP、Job、工作目录、资源和模式，仅一次 enqueue_only，allow_solver_submit=False。采用官方队列事务保护检查与写入，并在调用前独占保存 attempt 记录。没有直接编辑 Queue JSON/Project DB/AgentHub DB。

队列包含一个原有 run_014 完成记录及唯一待执行 P01。原历史记录逐字段保持不变，P02–P05 未入队。入队后资源、运行模式、输出身份及哈希核验通过；started_at/ended_at 为空、没有 ODB/LCK 或输出文件。Solver/datacheck 均未启动。Settings、Project DB、原 INP、冻结清单、live_status、最近项目和应用设置哈希保持不变，外部源码 Git 状态保持不变。

AgentHub 仅登记 enqueue 执行批准；用户手动 GUI 单次启动授权单独记录，未向 Codex 授予 start_solver/recover_retry。正式任务完成仅指入队工作完成，science_state=NOT_EVALUATED。授权、请求、队列状态和输出查询已登记，持久化 MAIN 消息不声称其他会话已接收。

## 文件与验证证据

- [准入](artifacts/admission.json)、[即时复核](artifacts/admission_before_enqueue.json)
- [授权](artifacts/authorization.json)、[公开 API 响应](artifacts/enqueue_response.json)
- [队列](artifacts/queue_after_enqueue.json)、[任务状态](artifacts/status_after_enqueue.json)、[输出定位](artifacts/outputs_after_enqueue.json)
- [结果](artifacts/enqueue_result.json)、[AgentHub 登记](artifacts/agenthub_receipt.json)、[证据哈希核验](artifacts/evidence_verification.json)
- 本轮新增 run_018 文件、更新 Run 索引和项目状态；授权的外部状态变化仅正式 Queue 和 AgentHub API 记录。未运行新的单元测试，执行的是上述实际准入及入队后验证。

## 停止点与研究限制

**P01 已入队，等待你在 AbqJobPilot GUI 点击 Start Queue。**

用户应打开 `E:\Projects\SMALL-PUNCH\agenthub_sp_invopt\abqjobpilot_project`，确认唯一待执行 Job 为 P01，然后手动点击一次。Codex 已停止执行链路，没有自动启动、重试或追加任务。求解结束后可按既有协议只读分析 ODB；失败不得自动重试，P02–P05 仍未授权。

模型适用性、夹持理想化与实验位移校正等既有科学不确定性保留；入队不构成求解成功或实验验证。隐藏拉伸数据未访问，保留“独立数据保留验证，存在历史信息暴露”历史记录。没有 commit/push。
