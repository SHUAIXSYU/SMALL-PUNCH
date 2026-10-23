# Run 索引

Run 用于记录独立研究任务的过程、证据路径与结果，不集中存储大型工程文件。

| Run | 阶段 | 目标 | 状态 | 总结 |
| --- | --- | --- | --- | --- |
| run_001 | Stage 1 | 基础架构、环境与资料审计 | WARNING | [summary](run_001/summary.md) |
| run_002 | Stage 1 | SP-InvOpt 中英文研究主页、RL/MDP 与路线图 | WARNING | [summary](run_002/summary.md) |
| run_003 | Stage 1 | 按启动文档与设计备忘录重构双语主页和详细研究导航 | WARNING | [summary](run_003/summary.md) |
| run_004 | Stage 1 | 记录默认研究 Python，核验实际导入与依赖一致性 | WARNING | [summary](run_004/summary.md) |
| run_005 | Stage 2 准入审计 | 现有 ODB 只读提取、Journal/INP 审计与正向准入判断 | WARNING | [summary](run_005/summary.md) |
| run_008 | SP-InvOpt AgentHub / AbqJobPilot 集成 | 三角色 SQLite 台账、INP 候选与只读 ODB/MCP 接入模拟 | WARNING | [summary](run_008/summary.md) |

每个 Run 必须包含 run.json、summary.md、artifacts/、checkpoints/；详见 [通信协议](../docs/Agent_File_Communication_Protocol.md)。私有证据目录不会随 Git 共享。编号建议不构成执行授权，run_005 完成后停止，不自动进入 run_006。


## 新授权 Run — run_006

| Run | 阶段 | 目标 | 状态 | 总结 |
| --- | --- | --- | --- | --- |
| run_006 | 本构数学审计 | 文献、工作簿与 Abaqus 材料定义一致性；独立 A/B/C 数值比较 | WARNING | [summary](run_006/summary.md) |

用户本轮已明确授权建立此 Run，前文 run_005 的停止记录为历史指令。run_006 已完成后停止，不自动进入 run_007。来源数值、公式细节及对比图保留在该 Run 的忽略私有区。


## 新授权 Run — run_007

| Run | 阶段 | 目标 | 状态 | 总结 |
| --- | --- | --- | --- | --- |
| run_007 | 候选材料参数化 | 可复用Hollomon生成器、自适应插值测试、历史PEEQ覆盖建议与新旧对照 | WARNING | [summary](run_007/summary.md) |

本轮用户明确授权候选实现，未授权物理验证结论或Solver。run_007完成后停止，不自动进入run_008。


## 新授权 Run — run_008

| Run | 阶段 | 目标 | 状态 | 总结 |
| --- | --- | --- | --- |
| run_008 | Agent 协作集成 | 独立 AgentHub、AbqJobPilot v0.2.2 Project/MCP 核验、候选 INP 与历史 ODB 接口模拟 | WARNING | [summary](run_008/summary.md) |

AgentHub 本地进程轮询、事务领取和结构化结果交接已验证；这不代表 Codex 会话自动收到通知。候选 INP 语法解析通过，但真实 AbqJobPilot Settings 文件缺失，preflight/dry-run 未运行；没有入队或启动 Solver。run_008 完成后停止，不自动执行 Solver Run。

## 新授权 Run — run_009

| Run | 阶段 | 目标 | 状态 | 总结 |
| --- | --- | --- | --- | --- |
| run_009 | AgentHub Runtime 补全 | JSON CLI、四角色身份范围、版本/失败诊断、共享 SQLite 非 Solver 验收 | WARNING | [summary](run_009/summary.md) |

Run 008 的独立台账和历史任务已保留并做增量迁移。软件交接测试通过；跨 Codex 会话自动唤醒、AbqJobPilot Settings 和真实科学求解仍未验证。本 Run 完成后停止，不自动进入下一 Run。


## 新授权 Run — run_010

| Run | 阶段 | 目标 | 状态 | 总结 |
| --- | --- | --- | --- | --- |
| run_010 | 真实会话集成 | MAIN→CAE真实任务交付、候选INP静态核验、稳定版Project/Settings审计 | BLOCKED | [summary](run_010/summary.md) |

真实CAE领取、证据登记和MAIN完成消息接收通过；Settings仍缺失，preflight/dry-run未执行，未入队/求解。


## 新授权 Run — run_011

| Run | 阶段 | 目标 | 状态 | 总结 |
| --- | --- | --- | --- | --- |
| run_011 | GUI Project 注册修复 | 官方API注册既有SP-InvOpt Project并回查用户级最近列表 | PASS（注册范围） | [summary](run_011/summary.md) |

Project/Queue/Settings保持，run_010的Settings与Solver阻塞仍有效。


## 新授权 Run — run_012

| Run | 阶段 | 目标 | 状态 | 总结 |
| --- | --- | --- | --- | --- |
| run_012 | 执行链路预检查 | Project Settings、候选身份和官方preflight/dry-run | BLOCKED | [summary](run_012/summary.md) |

官方预览在用户明确参数下实际通过；目标Project的Settings文件仍不存在。Queue为空未变，未求解；AgentHub已登记。


## 新授权 Run — run_013

| Run | 阶段 | 目标 | 状态 | 总结 |
| --- | --- | --- | --- | --- |
| run_013 | 持久化Settings准入复核 | 严格PERSISTED查询、重新预览、登记run_012阻塞解除证据 | PASS（工程预检查） | [summary](run_013/summary.md) |

run_012历史BLOCKED保留；其Settings阻塞已由本Run新证据解决。具备申请首次单次候选模型正向求解授权的工程条件，尚未入队或启动。

## 新授权 Run — run_014

| Run | 阶段 | 目标 | 状态 | 总结 |
| --- | --- | --- | --- | --- |
| run_014 | 首次授权正向求解 | 唯一候选、14 CPU/0 GPU、Datacheck+Full、单次入队与真实结果交接 | WARNING（已完成） | [summary](run_014/summary.md) |

唯一 Job `SPIO_R014_Q200_N010`，queue_id=`q_4c0358a918a7447d807d2f547d22c7b8`，Datacheck PASS、Full Analysis COMPLETED_WITH_WARNINGS，耗时165秒、零重试。真实ODB Agent已完成170点F–D提取与诊断，MAIN收到结果并核验14项Hub证据。末点力较历史差−0.07782、最大曲线差13.5922（模型单位）；39次拒绝尝试、4条负特征值及2条过度畸变警告保留。科学状态NOT_EVALUATED；本次授权已用完，新增求解须另行授权。

## 离线审计 Run — run_015

| Run | 阶段 | 目标 | 状态 | 总结 |
| --- | --- | --- | --- | --- |
| run_015 | SPT离线审计与盲反演协议 | 两源数值核对、真实ODB/CAE协作、Loss测试、探索契约冻结与泄漏登记 | WARNING（已完成） | [summary](run_015/summary.md) |

SPT候选数值集和PROVISIONAL对照已完成，12项合成Loss测试通过。正式单位/测量条件及数值门控待核验，新增FE为0。用户策略变更后封存保留验证资料；MAIN/ODB此前已接触，不能声称完全盲测。当前以[盲反演协议](../docs/Blind_Inversion_Protocol.md)为准，旧混合审计禁止继续读取；本轮结束，不自动求解或解盲。
