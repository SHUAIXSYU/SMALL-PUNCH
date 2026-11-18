# run_041 — BO/DE 八项授权批量入队

**WARNING / EIGHT_BO_DE_JOBS_QUEUED_AWAITING_MANUAL_START。** 本轮第一阶段完成，八项均为QUEUED，Datacheck与Solver未启动。现在停止执行，等待用户本人在正确Project点击一次Start Queue。

## 用户手动启动

AbqJobPilot Project：`E:\Projects\SMALL-PUNCH\agenthub_sp_invopt\abqjobpilot_project`。
Project ID：`b87d2cd6-8519-4ac3-bae6-7eb989fb2dae`。请在GUI核对以下8个可执行Job及顺序，再点击一次 **Start Queue**。

| 顺序 | Job | queue_id | 回读状态 |
| --- | --- | --- | --- |
| 1 | `SPIO_R040_BO01` | `q_6a1926161e9a47068e6af32188417ccc` | QUEUED |
| 2 | `SPIO_R040_BO02` | `q_224a3c8881144dc7b3d1ffadd3ae773b` | QUEUED |
| 3 | `SPIO_R040_BO03` | `q_6190d5cd054847dd9cd0e0de0f85cc5b` | QUEUED |
| 4 | `SPIO_R040_BO04` | `q_87629bc897334b6bba9ca443854ee1e3` | QUEUED |
| 5 | `SPIO_R040_DE01` | `q_8ea986fecc744003b63e27e04c561ba4` | QUEUED |
| 6 | `SPIO_R040_DE02` | `q_b7788b9b032340988313061d9a05f3dc` | QUEUED |
| 7 | `SPIO_R040_DE03` | `q_983e8f5e3e1c4eb699f47d33c0418744` | QUEUED |
| 8 | `SPIO_R040_DE04` | `q_48f294fd336444169d472bcc7807fa53` | QUEUED |

统一配置：14 CPU、0 GPU，Datacheck成功后Full Analysis，每个输入最多一次尝试、零自动重试、单Runner串行；只允许用户GUI启动。`AUTO_STOP_UNAVAILABLE`已经用户明确接受：一个Job失败或带警告后，Runner仍可能继续后续Job；Stop After Current Job是人工请求，不能视为可靠自动异常停机。

## 身份、当前预检及预算

- 实际最大历史Run为run_040，独占创建run_041。读取AGENTS/Run/AgentHub协议、run_039与run_040报告，记录main分支、HEAD及既有工作树，不覆盖历史证据或用户改动。
- 冻结参数清单SHA-256为 `692c3215c974b35ea1c816b86520f2c183241504c8bd2e0b111cda44bb2d502b`。该清单原本冻结算法参数及路径，完整INP哈希来自其绑定的既有CAE生成清单与run_040 MAIN审核；三者在本轮联接核验，未重新生成输入。8份INP、参数JSON、生成器和模型契约哈希全部匹配，非材料源字节一致，工作目录相互独立且为空。
- 数值契约 `run030-standard-m0025-hollomon-v1`，Loss契约 `run017-exploratory-fd-v1` 原版本保持绑定；初始增量0.001、最大0.0025、最小1e-12、总时间1、最大增量数999999、E=210 GPa、ν=0.3。没有根据候选修改几何、网格、接触、摩擦、BC、Punch加载或输出。
- 本机实际导入AbqJobPilot 0.2.2，公开API Project身份和 `PERSISTED` Settings通过，Abaqus命令 `D:\ABAQUS2024\Commands\abq2024.bat` 存在，14 CPU/0 GPU及Datacheck/Full均匹配；本轮重新执行8/8 Preflight和8/8 Dry-run均就绪。预览阶段Queue/Settings/Project DB哈希未变；真实入队只使用公开API，入队后Settings和Project DB仍不变。
- Runner所有权ABSENT、Live为IDLE、运行恢复评估CLEAN、Abaqus进程探测CLEAR，没有其他可执行Job。原run_033 D09历史目录仍有旧锁；该旧Job中断历史及既有官方恢复记录保留，锁不属于八个新目录，未打开旧ODB或清锁。通用恢复计划仍提示该历史锁，未将它误报成新Job活动状态。
- 本机 `runner_core.py` 的 `_run_loop` 在 `run_next_job(job)` 后不检查求解结果而继续选下一个Job，当前代码SHA已登记，异常自动停队列仍不可用。
- MAIN通过正式Hub接口登记8次预算、每项输入完整hash、Project、资源、手动启动方式及独立审批；依次入队并记录8个唯一queue_id。最终回读顺序完全匹配，只有本批8项可执行，均无started_at/ended_at、没有新ODB或锁且工作目录为空。
- 当前预算：授权8、准备8、入队8、实际启动0、消耗FE尝试0。八项额度全部绑定上述输入；未来任何已启动尝试无论成功失败都会消耗对应一次，不能转成替代参数、重试或追加Job。第二阶段额外8次未授权。

## AgentHub及第二阶段停止点

预算登记任务：`05f15fab-278a-435c-b914-87802cd81539`；八项Queue任务及总体验证均COMPLETED/RECORDED，但只代表入队工作完成，科学状态NOT_EVALUATED。后续MAIN执行审计、ODB批量只读提取、MAIN科学比较任务已登记；ODB依赖真实执行审计完成，目前未唤醒ODB会话，也未宣称结果提取。用户通知计算完成后才审计真实终态，逐项区分完成、失败、中断、未启动及科学可评分状态。BO四点仍是固定batch提议，DE四点仍是半代，不得事后改算法或利用对方新增结果重选点。

私有授权范围、逐项API请求/响应、真实queue_id、最终Queue回读和预算账本位于 `artifacts/private/`。封存拉伸文件和派生结果未访问；历史信息泄漏及run_025 BLOCKED等结论保持。未调用Abaqus、Datacheck或GUI启动，无RL、第二阶段优化、commit/push。
