# run_014 — First authorised Hollomon forward validation

**WARNING。唯一授权 Job 已完成，Datacheck PASS；Full Analysis COMPLETED_WITH_WARNINGS；真实 ODB Agent 完成只读提取，MAIN 已收到并核验结果。科学状态 NOT_EVALUATED。**

## 唯一执行身份

| 标识 | 值 |
| --- | --- |
| 授权/入队 task_id | 93322987-9489-47c1-908a-dd43e0736339 |
| 终态证据 task_id | 21e7ccb4-7061-4cdb-ad73-9506ee7c424d |
| 真实 ODB task_id | 35b07ba1-22ad-48a7-b859-2d99199ed419 |
| MAIN 复核 task_id | b082d706-fe59-432f-9541-c050edb998ff |
| queue_id | q_4c0358a918a7447d807d2f547d22c7b8 |
| Job | SPIO_R014_Q200_N010 |
| Project ID | b87d2cd6-8519-4ac3-bae6-7eb989fb2dae |
| CPU / GPU | 14 / 0 |
| 尝试 / 自动重试 | 1 / 0 |

原始输入为 [run_008 候选 INP](../run_008/artifacts/candidate_inp/SPIO_R008_Q200_N010_Candidate/SPIO_R008_Q200_N010_Candidate.inp)，未修改或复制。SHA-256：`fa2de5d73a28536c1c07cd22072d2a24c1ae988c569127d728931c583457f05a`。参数 sigma_y=200 MPa、n=0.1、E=210 GPa、nu=0.3、max_plastic_strain=0.9。所有新 Solver 输出位于用户指定的独立目录 `run/run_014/artifacts/solver/SPIO_R014_Q200_N010`，该目录单独忽略，不覆盖历史 Job-1。

新 ODB SHA-256：`1ed3ecb6b2e3e2bfcfc806eb7edfab706b4acc90ec387ac641a81f529d9dd4fd`。ODB/STA/MSG/DAT/LOG 的实际路径、大小、SHA-256，以及 public status/locate_outputs/history 原始返回均见 [终态证据](artifacts/solver_terminal_result.json)。

## 实际操作和阶段结果

1. 遵循实际 AGENTS、Run 协议、run_013 和 Hub 契约；核对索引并独占创建合法 run_014。Git 基线 main / e87aadc9f7074fc4bc127c9ae03afbe9081dabae，原有用户改动保留。使用已登记 Torch-GPU 的绝对解释器，Python 3.11.13 / SQLite 3.50.2，无依赖安装。
2. 严格 Project ID 查询返回 PERSISTED，无默认字段补齐，API/磁盘/effective_settings 一致。Abaqus `D:\ABAQUS2024\Commands\abq2024.bat` 存在，14 CPU、GPU关闭/0、Datacheck/Full开启、Auto shutdown关闭。修复版 AbqJobPilot 0.2.2，源码 HEAD 7012133e7cc0176bb3e56fc24d7154ee3b90bb81，工作树干净。
3. 输入 hash 与 run_013 匹配；有效关键字无 INCLUDE/IMPORT/FILE/INPUT/LIBRARY/OLDJOB 外部引用或 RESTART READ，只有 RESTART WRITE。独立工作目录为空、无进程或文件冲突；Queue为空、Runner ABSENT/IDLE，无中断/恢复状态。新 Job 名及目录的 preflight=PREVIEW_READY，dry-run=DRY_RUN_READY。见 [硬性检查](artifacts/admission_before_enqueue.json)。
4. MAIN 在既有 Hub 建立不可变范围 payload，分别登记 enqueue 和 start_solver approval，未授予 recover_retry。Hub 继续仅记录权限和证据，没有修改其历史禁用的外部执行器；实际入队采用官方公开 API。
5. 原生事务内再次检查空 Queue、输入及配置后，仅调用一次 `enqueue(..., dry_run=False)`，显式 enqueue_only、allow_solver_submit=false 和全部资源/阶段/工作目录参数。回读 Queue恰有本 Job。调用前的独占 attempt 标记阻止脚本重复入队，未知结果也不能自动重试。[请求](artifacts/request.json)、[API响应](artifacts/enqueue_response.json)、[队列快照](artifacts/queue_after_enqueue.json)。
6. MAIN明确提示用户GUI Start Queue后，用户确认“已点击一次 Start Queue”；MAIN没有调用 Solver CLI/subprocess/Runner/GUI自动化启动。Runner在同一 Job 中 Datacheck通过后进入Full Analysis。

| 阶段 | 本地时间（UTC+08:00） | 结果 |
| --- | --- | --- |
| 入队 | 22:12:48 | ENQUEUED，未启动 |
| Datacheck | 22:13:49—22:14:25 | 返回码0，PASS |
| Full Analysis 命令 | 22:14:25—22:16:33 | 返回码0，正常完成 |
| Queue终态 | 22:16:34 | COMPLETED_WITH_WARNINGS，SUCCESS |

以上日期均为2026-10-21。AbqJobPilot实际记录总耗时 **165秒**（包含两阶段与Runner收尾）；不是预测时间。MSG内Full求解器自身wallclock为100秒，两种统计口径不同。日志恰有一次Datacheck和一次Full的START/END，没有第二个Job、重试或重入队。

## 真实 ODB 协作与结果

Full完成后，MAIN确认锁释放、输出稳定并登记终态证据，创建正式ODB任务。通过Codex消息工具通知既有 `SP-InvOpt ODB` 会话 `01a15d5e-f6e8-7373-8991-ae275dfd3b40`；该真实会话以ODB身份实际轮询/领取第1代租约、执行提取、登记14项证据并发送持久完成消息。MAIN回读完成状态、生产者/会话、所有登记文件哈希和消息，并独立重算曲线差异；不是模拟worker或仅写收件箱。[真实claim](artifacts/real_odb_claim_observed.json)、[MAIN收件回执](artifacts/main_received_odb.json)、[MAIN复核](artifacts/main_reconciliation.json)。

Abaqus 2024 Python 3.10.5以 `readOnly=True` 打开新ODB，内部状态 `JOB_STATUS_COMPLETED_SUCCESSFULLY`，0分析错误。Punch RP `ASM_SPT.1` 与候选刚体/节点集对应，U2/RF2共享时间轴，History与Field在170帧逐点一致。原始符号保留，正向 `d=-U2, F=-RF2`，不取绝对值、不平滑、不加2π。

| 指标（模型单位） | 新run_014 | 历史Sanity Job-1 |
| --- | ---: | ---: |
| F–D采样点 | 170 | 181 |
| 末点正向位移 | 0.001200000057 | 0.001200000057 |
| 末点/保存峰值正向力 | 755.8150635 | 755.8928833 |

末点差为 **−0.0778198（−0.010295%）**。将历史力按位移线性插值到新曲线170点后，最大绝对力差 **13.5922**（位移0.000160815），RMS差 **6.13379**。这是两次模型计算的描述性比较，不能由末点接近推出整条曲线重合、材料有效或实验拟合准确。物理单位声明仍未独立确认，CSV/图使用模型单位；历史ODB哈希与run_005一致，未修改、未冒充新候选结果。

保存帧最大积分点PEEQ **0.6938983 < 0.9**，材料表覆盖裕量0.2061017；该结论仅适用于保存帧，不保证未保存试算态。F–D积分与ALLWK差约5.83e−8模型能量单位；完整接触能量平衡仍未独立验证。

见 [ODB完整诊断](artifacts/odb/report.md)、[F–D CSV](artifacts/odb/punch_force_displacement.csv)、[原始符号CSV](artifacts/odb/punch_history_raw.csv)、[新旧曲线](artifacts/odb/force_displacement_comparison.png)、[结构化诊断](artifacts/odb/diagnostics.json)。

## 警告、失败记录及完整性

- 169个接受增量、39次拒绝尝试/cutback；历史为180个接受增量、45次拒绝尝试。35条MSG分析警告中有4条负特征值、2条过度畸变、25条应变增量过大、2条未尝试塑性积分及2条零力矩警告。负特征值/过度畸变均对应被拒绝试算态，最终收敛不等于网格/增量敏感性已验证。
- AbqJobPilot聚合警告38、MSG分析警告35、ODB诊断警告6属于不同统计范围，不能相互替代；ODB/MSG分析错误为0。
- Full阶段native进程聚合仍为UNCONFIRMED：短暂PID14320在身份采集前已消失。完整身份的launcher/pre.exe/standard.exe等均确认退出，当前PID列表无14320，Runner ABSENT/IDLE、无.lck、输出哈希及间隔稳定；MAIN和ODB各自独立确认当前只读安全。历史进程身份缺口保留，未修改外部审计状态、清锁或授权恢复。
- MAIN终态证据脚本两次只读收集停止：先遇终态live不含活动process_identity字段，后因上述native缺口停止；错误与旧脚本保留。改为读取正式phase evidence并补充独立当前读取安全证据。ODB首次只读导出因Repository不支持.get()失败，保留诊断后修正提取。上述均非Solver重试，未改变输入或求解参数。
- 候选INP、原始CAE、历史ODB、Hollomon源、Settings、run_013记录及外部源码均保留。Project DB由正式Runner记录执行历史；用户GUI打开Project后recent_projects的last_opened_at更新为22:13:45。MAIN未直接编辑任何Queue JSON、Project DB、Hub DB或recent配置。代码、报告、证据留在仓库新Run；未commit/push、未训练。

## MAIN 科学结论与授权边界

本轮完成了一次有输入身份、显式授权、单Job执行、正式历史、真实ODB会话及持久回执的工程闭环。候选仍采用真总应变解释，未获得实验验证；单位确认、模型边界意图、网格/增量敏感性和材料科学有效性仍需后续研究，不能据此启动反演或训练。

此次单次授权已经用完，当前没有待执行Job。**任何进一步Solver计算、重试、改参数或新Job均需新的明确授权**；本Run到此结束，不自动进入下一Run。
