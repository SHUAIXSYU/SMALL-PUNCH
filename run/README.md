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


## 新授权 Run — run_016

| Run | 阶段 | 目标 | 状态 | 总结 |
| --- | --- | --- | --- | --- |
| run_016 | Experimental-to-FE Qualification | 合作方声明、真实 CAE/ODB 准入审计、Loss 复核及分阶段预算 | BLOCKED（正式反演准入；离线完成） | [summary](run_016/summary.md) |

几何/夹具等效与载荷单位仍未解决；位移声明改善对应依据，Loss/窗口保持 PROVISIONAL。19 项合成测试通过，公开依据探索域和条件式预算已登记。新 Job 授权/执行均 0；保留历史信息暴露，不再访问保留拉伸数据。完成后停止。


## 新授权 Run — run_017

| Run | 阶段 | 目标 | 状态 | 总结 |
| --- | --- | --- | --- | --- |
| run_017 | First Constitutive Sensitivity Study Preparation | 来源确认、探索性 Loss 冻结、真实 CAE 五输入及公开 API 预览 | WARNING（准备完成） | [summary](run_017/summary.md) |

来源方澄清力单位，名义几何一致；用户接受理想化夹持作为本批基线。五个 INP/Preflight/Dry-run 就绪，28 项合成测试通过；可以申请最多五个探索性 Job，授权/入队/执行均0。完整夹具等效、位移校正与材料科学有效性仍未验证；完成后停止。


## run_018 — P01 Queue-only Submission

| Run | 阶段 | 目标 | 状态 | 总结 |
| --- | --- | --- | --- | --- |
| run_018 | P01 Queue-only | 唯一冻结 P01 正式入队；用户 GUI 手动启动 | PASS（入队范围） | [summary](run_018/summary.md) |

P01 唯一待执行；Datacheck/Full 均未启动，P02–P05 未入队。停止等待用户 GUI。


## run_019 — 已有计算结果分析

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_019 | 真实ODB交接、冻结Loss与可用敏感性证据审核 | WARNING（缺少扰动结果） | [summary](run_019/summary.md) |

分析结果保存在忽略的私有区；新入队/求解为0，完成后停止。


## run_020 — 局部敏感性设计调整

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_020 | 条件式中心复用、真实CAE四输入及公开API预览 | WARNING（离线准备完成） | [summary](run_020/summary.md) |

旧设计保留；计算授权、入队、新Solver均0，后续须独立授权。


## run_021 — 四点授权 Queue-only 入队

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_021 | 四点正式入队、本机Runner异常控制审计 | WARNING / AWAITING_MANUAL_START | [summary](run_021/summary.md) |

四项QUEUED，AUTO_STOP_UNAVAILABLE；用户GUI手动启动，Codex未启动求解，停止等待。


## run_022 — 四点真实结果与局部可识别性

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_022 | 真实ODB提取、冻结五点Loss、局部Jacobian及数值审查 | WARNING（分析完成） | [summary](run_022/summary.md) |

用户GUI完成四项，MAIN没有新增计算；数值风险未解除，后续须另行授权。


## run_023 — Numerical Robustness Qualification

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_023 | 既有数值事件审计、两项增量细化输入及冻结评价契约 | WARNING（准备完成，未求解） | [summary](run_023/summary.md) |

真实CAE/ODB完成，公开预检查通过；没有入队或求解。停止等待明确计算授权。


## run_024 — 两阶段验证授权：V01入队

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_024 | 冻结V01单项Queue-only与条件预算登记 | WARNING / V01_QUEUED_AWAITING_MANUAL_START | [summary](run_024/summary.md) |

V02未入队，须V01数值资格PASS；停止等待用户GUI启动。


## run_025 — V01真实数值资格审核

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_025 | 真实ODB提取、冻结精度门槛与V02准入判断 | BLOCKED_V01_NUMERICAL_QUALIFICATION | [summary](run_025/summary.md) |

V01求解完成但精度门槛失败；V02未入队，停止等待新科研决策。


## run_026 — V01 数值差异定向诊断

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_026 | 既有F–D、接触场与数值事件的局部归因及科研影响 | WARNING（离线完成；run_025门槛仍BLOCKED） | [summary](run_026/summary.md) |

V02未入队；下一步建议另行授权一个中心定向验证，未执行新求解。

## run_027 — 单一中心点增量细化准备

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_027 | 真实CAE单候选、冻结相邻细化比较、公开API预览 | WARNING（离线准备完成） | [summary](run_027/summary.md) |

未入队或求解；run_025数值资格仍BLOCKED，V02不可执行，停止等待新授权。

## run_028 — 单一中心点授权 Queue-only

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_028 | run_027 唯一候选正式入队；等待用户GUI启动 | WARNING / AWAITING_MANUAL_START | [summary](run_028/summary.md) |

唯一Job已QUEUED；Codex未启动Solver，停止等待用户手动Start Queue。

## run_029 — 中心点真实结果与相邻细化资格

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_029 | 真实ODB交接、冻结五项门槛、局部接触与数值警告审核 | WARNING / PASS_CENTER_ADJACENT_REFINEMENT_ONLY | [summary](run_029/summary.md) |

原run_025数值资格BLOCKED不变；V02未入队，停止等待新的研究授权。

## run_030 — 16次探索性反演离线准备

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_030 | 冻结8+4+4预算、八份统一数值控制输入、真实CAE交接与公开预览 | WARNING / READY_TO_REQUEST_STAGE_A_WITH_GATES | [summary](run_030/summary.md) |

未入队或求解；I01–I04 首先需新的具体授权并逐项审核。

## run_031 — 八项授权与I01单项入队

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_031 | 登记8项冻结授权、逐项门控、仅I01 queue-only入队 | WARNING / I01_QUEUED_AWAITING_MANUAL_START | [summary](run_031/summary.md) |

I01等待用户GUI手动Start Queue；其余7项未入队，完成与审核后才逐项继续。

## run_032 — I01真实ODB审核与I02单项入队

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_032 | I01真实ODB、冻结Loss、MAIN门控和I02 queue-only入队 | WARNING / I02_QUEUED_AWAITING_MANUAL_START | [summary](run_032/summary.md) |

I01单次尝试已完成；I02为唯一待执行Job，等待用户GUI手动Start Queue；I03–I08未入队。

## run_033 — 20 Job DOE batch queue-only

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_033 | I02终态、14新DOE、真实CAE、20/20预览与批量入队 | WARNING / TWENTY_JOBS_QUEUED_AWAITING_MANUAL_START | [summary](run_033/summary.md) |

20项QUEUED，等待用户在正确Project手动点击一次Start Queue；AUTO_STOP_UNAVAILABLE风险已确认。

## run_034 — 20项 DOE 真实结果审计

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_034 | 20项真实执行审计、真实ODB交接、冻结Loss及DOE地形 | WARNING / 17 scored, 3 null | [summary](run_034/summary.md) |

19项软件完成，D09中断状态不明；D07/D10数值警告保守不评分。无新求解或优化。

## run_035 — D09 崩溃重试 Queue-only

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_035 | 复用冻结 D09 输入，建立独立重试身份并仅入队一次 | WARNING / AWAITING_MANUAL_START | [summary](run_035/summary.md) |

旧 D09 UNKNOWN_INTERRUPTED 及锁文件保留；新 Job 等待用户手动 Start Queue。

## run_036 — D09 二次中断与恢复评估

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_036 | 只读核验第二次尝试与官方恢复准入 | BLOCKED / RECOVERY_REQUIRED | [summary](run_036/summary.md) |

旧记录保留；恢复计划不可应用，未新增入队或求解。

## run_037 — D09 重启后恢复准入复核

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_037 | 重启后只读复核 D09 第三次尝试准入 | BLOCKED / RECOVERY_REQUIRED | [summary](run_037/summary.md) |

未新增入队或求解。

## run_038 — D09 第二次独立重试

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_038 | 官方恢复后原冻结 D09 输入单项 queue-only 入队 | WARNING / AWAITING_MANUAL_START | [summary](run_038/summary.md) |

等待用户在 GUI 手动 Start Queue。

## run_039 — 20项 DOE 批量结果分析

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_039 | 原20项与I01/I02及独立D09补算审计、冻结Loss、补偿与BO/DE准入 | WARNING / 19 scored, 3 null | [summary](run_039/summary.md) |

原20项19项软件完成、D09原始中断；22参数点19项探索性评分。无新求解或优化。

## run_040 — BO/DE 先导优化离线准备

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_040 | 19点共享数据、批量BO与部分代DE、真实CAE生成8份输入及预览 | WARNING / READY_TO_REQUEST_FIRST_GATE_WITH_NUMERICAL_RISK | [summary](run_040/summary.md) |

8/8 Preflight和dry-run通过；无入队、Datacheck或Solver。

## run_041 — BO/DE 八项授权批量入队

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_041 | 8项冻结输入授权登记、当前预览及公开API批量queue-only入队 | WARNING / EIGHT_BO_DE_JOBS_QUEUED_AWAITING_MANUAL_START | [summary](run_041/summary.md) |

8项QUEUED，0次实际启动；等待用户GUI一次Start Queue。AUTO_STOP_UNAVAILABLE风险已接受。

## run_042 — BO/DE 先导真实结果

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_042 | 8项实际审计、真实ODB提取、冻结Loss与BO/DE科学比较 | WARNING / 5 scored, no D01 improvement | [summary](run_042/summary.md) |

8项软件完成、5项可评分，三项null；建议先数值资格与不确定性研究，无新求解。

## run_043 — 低Loss可识别性与数值资格准备

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_043 | D01/I08残差及预测本构、排序协议、真实CAE两项增量验证输入与预览 | WARNING / PREPARED_NO_SOLVER_AUTHORIZATION | [summary](run_043/summary.md) |

2/2 Preflight和dry-run通过；无入队或求解，等待新授权。

## run_044 — 两项数值验证授权入队

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_044 | D01/I08冻结验证输入授权登记、当前预检查与一次性queue-only入队 | WARNING / TWO_VALIDATION_JOBS_QUEUED_AWAITING_MANUAL_START | [summary](run_044/summary.md) |

两项QUEUED，0启动，等待用户GUI一次Start Queue。

## run_045 — D01/I08 真实数值细化与可识别性

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_045 | 两项真实ODB、冻结五指标、Loss排序与竞争本构 | WARNING / PASS_TWO_POINT_ADJACENT_REFINEMENT_ONLY | [summary](run_045/summary.md) |

未启动新求解或解盲，历史BLOCKED保留，完成后停止。

## run_046 — 候选本构冻结与独立验证准备

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_046 | 冻结两组本构及SPT结果，预注册独立验证并封装hash证据 | WARNING / FROZEN_AWAITING_EXPLICIT_UNBLIND_AUTHORIZATION | [summary](run_046/summary.md) |

不解盲、不求解；停止等待用户明确授权。

## run_047 — 冻结后独立拉伸核查

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_047 | 用户授权的独立解盲、冻结核验与预注册验证门控 | WARNING / PRIVATE_INDEPENDENT_REPORT_FINALIZED | [summary](run_047/summary.md) |

全部实验数字及解盲结论留在本 Run 的 Git 忽略私有审计区。无新求解或优化；完成后停止。

## run_048 — 合作方补证后的独立复核

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_048 | 新来源方回复下重核冻结门控与受限数值比较 | WARNING / PRIVATE_REASSESSMENT_FINALIZED | [summary](run_048/summary.md) |

科学结论和可恢复拉伸数字仅在本 Run 的忽略私有区；无新求解或优化，完成后停止。


## run_049 — 验证后科研评估与研究设计

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_049 | 历史FE补偿证据、材料形式与夹具不确定性分阶段研究设计 | WARNING / OFFLINE_SCIENTIFIC_ASSESSMENT_COMPLETE | [summary](run_049/summary.md) |

正式验证维持NOT_EVALUABLE；私有证据不公开，无新增求解、拟合、入队或优化。完成后停止。


## run_050 — 高塑性应变空间、能量与外推风险

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_050 | 真实ODB空间/能量只读提取、MAIN独立核验与最小机制验证设计 | WARNING / EXISTING_ODB_SPATIAL_ENERGY_REVIEW_COMPLETE | [summary](run_050/summary.md) |

近似能量不作RF2分解；正式验证与历史结论保留，无新输入、拟合或求解，完成后停止。


## run_051 — D01高应变硬化包络准备

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_051 | 塑性功口径核对、两份低段保持的材料包络及真实CAE预览 | WARNING / READY_TO_REQUEST_TWO_EXPLORATORY_SOLVES | [summary](run_051/summary.md) |

无新求解/入队/优化，不修改原预测，完成后停止。


## run_052 — H01/H02授权Queue-only入队

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_052 | 两项冻结高应变包络授权、现行预检及公开API入队 | WARNING / TWO_HARDENING_JOBS_QUEUED_AWAITING_MANUAL_START | [summary](run_052/summary.md) |

两项QUEUED、0启动/消耗，等待用户GUI手动Start Queue；尚未开展结果分析。


## run_053 — H01/H02求解后高应变硬化敏感性

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_053 | 两项真实执行审计、ODB提取、MAIN独立Loss/空间能量复核 | WARNING / TWO_EXISTING_RESULTS_ANALYSED | [summary](run_053/summary.md) |

科学明细留私有区，原两次尝试已消耗，本轮无新求解、入队、拟合或优化，完成后停止。


## run_054 — 离线参数方向与高应变混淆

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_054 | 核对跨基点/数值契约，量化方向、残差及识别证据等级 | WARNING / OFFLINE_CONFOUNDING_ASSESSMENT_COMPLETE | [summary](run_054/summary.md) |

正式联合指标NOT_EVALUABLE，科学明细留私有区，无新计算/入队/拟合，完成后停止。


## run_055 — 特征反演与全曲线留出对照

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_055 | 唯一样本盘点、固定特征、嵌套CV及识别歧义 | WARNING / PARTIAL_FE_PARAMETER_RECOVERY_ONLY | [summary](run_055/summary.md) |

只支持有限样本FE自洽恢复，不构成可靠材料公式；当前新FE预算0，无输入/入队/优化，完成后停止。


## run_056 — Git治理及前瞻性特征识别

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_056 | CAE索引/忽略治理、低n门控复核及四点前瞻协议 | Git PASS / Science WARNING | [summary](run_056/summary.md) |

本地CAE完整，仅2项解除索引；无新输入、求解或入队，执行预算0，完成后停止。


## 新授权 Run — run_057

| Run | 阶段 | 目标 | 状态 | 总结 |
| --- | --- | --- | --- | --- |
| run_057 | Prospective Identification Batch Preparation | I06四点材料变体、冻结预测器与公开预览 | WARNING（仅准备） | [summary](run_057/summary.md) |

四输入/完整SHA与A/B前瞻协议冻结，4/4预检和dry-run通过；I06带限制，11项测试通过，新FE/入队0。仅可申请明确四Job运行授权，当前完成后停止。


## 新授权 Run — run_058

| Run | 阶段 | 目标 | 状态 | 总结 |
| --- | --- | --- | --- | --- |
| run_058 | Four-point prospective identification queue-only | 四项冻结身份/预测器核验、授权登记与公开API入队 | WARNING（等待人工启动） | [summary](run_058/summary.md) |

4/4预检和Dry-run通过，按P01→P04仅入队四项、实际启动/FE消耗0。等待用户GUI Start Queue；AUTO_STOP_UNAVAILABLE风险已接受，第二阶段尚未开展。


## 新分析 Run — run_059（run_058 Phase2）

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_059 | 真实四ODB、MAIN复核、冻结A/B前瞻识别 | WARNING / LIMITED / PARTIAL | [summary](run_059/summary.md) |

4/4单次完成且探索性可评分；全曲线预测优于常数但未通过完整半步目标，当前新FE预算0，完成后停止。


## 新准备 Run — run_060

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_060 | 唯一I06增量细化输入、弱方向比值及比较协议冻结 | WARNING（仅准备） | [summary](run_060/summary.md) |

仅最大增量.0025→.00125，Preflight/Dry-run及8项测试通过；当前新FE授权0、未入队/求解，完成后停止等待单独授权。


## 新授权 Run — run_061

| Run | 阶段 | 目标 | 状态 | 总结 |
| --- | --- | --- | --- | --- |
| run_061 | I06 single refinement queue-only | run060唯一冻结输入授权核验、公开API入队 | WARNING（等待人工启动） | [summary](run_061/summary.md) |

1/1预检通过，仅1个QUEUED；实际启动/消耗0。Phase1结束，等待用户GUI Start Queue及完成通知，Phase2未执行。


## 新结果 Run — run_062（run_061 Phase2）

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_062 | 真实I06细化ODB、独立数值复核、冻结比较和弱方向R | WARNING / 点级SUPPORTED / 识别LIMITED | [summary](run_062/summary.md) |

单次完成、RMSE .432677914N、R .139906018（.1–.25提示），不升级run059。当前分析新增FE/入队/重试0，完成后停止。


## 离线科研 Run — run_063

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_063 | 局部参数耦合、分段/特征SVD、确定性响应扰动情景 | WARNING / LIMITED | [summary](run_063/summary.md) |

真实旧FE核验，弱方向σy↓/n↑；完整曲线保留为主基线，不生成直接材料公式。当前新FE/训练/入队0；未来弱方向混合±2点仅建议，完成后停止。


## 交流报告 Run — run_064

| Run | 目标 | 状态 | 报告 |
| --- | --- | --- | --- |
| run_064 | 既有真实结果的4页中文合作报告及科学图件 | 交付PASS / 科学WARNING保持 | [summary](run_064/summary.md) |

仅报告制作与既有指标复核；私有证据不公开，无新求解/训练/拟合，完成后停止。
