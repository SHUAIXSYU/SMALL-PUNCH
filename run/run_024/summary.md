# run_024 — 两阶段数值验证授权：V01 Queue-only

**WARNING / V01_QUEUED_AWAITING_MANUAL_START。本Run完成第一阶段入队；两项数值验证研究尚未完成。**

| 项目 | 实际状态 |
| --- | --- |
| V01 Job | SPIO_R023_V01_CTR |
| queue_id | q_602fa04221884dc7b200d670c610c385 |
| MAIN入队任务 | 7d281a3e-729e-4b4e-96c7-b4128f1f35f3 |
| 两阶段预算登记任务 | b6fcf7ca-f82d-4ac0-8c4c-8ec61bb120dc |
| Project ID | b87d2cd6-8519-4ac3-bae6-7eb989fb2dae |
| CPU / GPU | 14 / 0 |
| Datacheck / Full | True / True，均未启动 |
| V01数值资格 | NOT_EVALUATED |
| V02 | 未入队；须V01数值审核PASS后才能安排 |
| 每Job上限 / 自动重试 | 一次两阶段尝试 / 0 |

用户正式授权两项冻结Job，逐项入队、用户GUI启动，失败同样消耗对应授权。当前只有V01为QUEUED；V02授权有条件保留，无须在V01真正PASS后重复申请，但必须重新检查Runner、恢复状态、队列与输入身份。WARNING/BLOCKED时禁止V02入队。没有第三项、中心重算以外的额外参数计算或DE/BO/RL授权。

## 已执行核验

读取AGENTS、Run/AgentHub/盲反演协议及run014/022/023报告，独占创建下一合法run024。选用已登记迁移后的Torch-GPU绝对解释器，Python3.11.13/SQLite3.50.2，未安装依赖。Git基线及用户已有改动留档，无commit/push。

冻结批次整体hash对照run023 manifest，两个输入完整SHA及其对应基线均核对；每份新输入仅含批准的Static数据行差异，材料、物理模型与其他字节一致。初始.001、最大.005、总时间1、最小1e-12、inc999999；没有重新生成输入、没有外部文件依赖。V01 SHA-256 `14006d69c15e6fd4be021b889964e5add51e724d52fd03ff817b0f80b747c2ff`。输入及输出绝对路径见[入队结果](artifacts/enqueue_result.json)，工作目录在run023冻结位置，不迁移文件。

修复版公开API核实Project ID/路径，Settings=PERSISTED，无默认值补齐；Abaqus2024命令真实存在、14CPU/0GPU、Datacheck/Full开启、Auto shutdown关闭。Runner owner=ABSENT、live=IDLE、只读recovery assessment=CLEAN，无目标/求解进程冲突、无锁、无其他可执行Queue记录；Queue和History均无既有V01/V02尝试，两目录为空。

V01 preflight=PREVIEW_READY、dry-run=DRY_RUN_READY。通过公开enqueue_only、allow_solver_submit=False，仅一次真实enqueue；调用前保存独占attempt记录，重复执行受阻并须只读核对，不可自动重试。使用官方运行时事务防止检查与入队间GUI获取Runner。真实回读确认唯一可执行V01、完整身份/资源/阶段/输出目录一致，旧终态条目保持不变，V02无记录。API status为QUEUED，无ODB/LCK，无开始/结束时间。Solver/datacheck/Runner均未由Codex启动。

Queue变化由公开API完成；project.db、Settings、原始输入、冻结比较契约和历史Run结论未变，没有直接改写内部持久化状态。AgentHub正式API登记总预算及V01 enqueue approval，未授予Codex start_solver/retry；记录了输入hash、queue_id、执行状态和剩余条件授权。ODB任务等待真实求解结束后创建，不将消息入库当作自动唤醒会话。

## 人工停止点与后续门控

请在正确Project确认只有V01待执行，再由用户点击一次Start Queue。AUTO_STOP_UNAVAILABLE继续保留；目前坚持单Job可执行队列。入队不是求解成功，也不是数值精度PASS。

V01完成后，新结果审计通过正式API和真实ODB会话提取，MAIN按run023-increment-qualification-v1及run017-exploratory-fd-v1复核。不得修改已冻结阈值、窗口或相对差分母。全部指标及数值风险门控通过才使用PASS_V01_NUMERICAL_QUALIFICATION；否则WARNING_V01_REVIEW_REQUIRED或BLOCKED_V01_NUMERICAL_QUALIFICATION，并保持V02不入队。当前没有任何新F-D/Loss/PEEQ或精度结论。用户需回到MAIN确认完成以继续；未设置自动轮询唤醒。

修改范围：新run024证据、正式Hub任务、公开API单项Queue、Run索引和状态。封存拉伸数据未读取，历史信息暴露声明不变。完成当前入队指令后停止。
