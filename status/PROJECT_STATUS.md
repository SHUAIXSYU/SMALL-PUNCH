# SMALL-PUNCH 项目状态

## 当前状态 — run_018（2026-10-23，Asia/Shanghai）

**PASS（唯一 P01 入队范围）：QUEUED / AWAITING_GUI_START。** 用户授权已通过正式公开 API 完成一次入队，Job `SPIO_R017_P01_CTR`，queue_id `q_bdec6a60a31849d0a2afe200a70231bd`，CPU14/GPU0，Datacheck+Full=True。只有 P01 待执行；Solver/datacheck 尚未启动，P02–P05 未授权入队。本任务已停止，等待用户在正确 Project 的 GUI 点击一次 Start Queue。

正式 Project Settings=PERSISTED，冻结完整哈希、预览、Runner/输出冲突检查及入队后核验通过。AgentHub task `37ad24d5-26af-4374-b415-c6a1af1fc0c7` 已登记授权和证据。见 [run_018 报告](../run/run_018/summary.md)。求解成功及物理有效性尚未评估，无自动重试；此前 run_017 结论保留在下方。


## 当前状态 — run_017（2026-10-23，Asia/Shanghai）

**WARNING（离线准备完成）：具备申请最多五个探索性局部敏感性 Job 的条件；当前求解授权、实际入队和新 FE 均为 0。** 合作方确认力/位移单位及球径，名义几何一致；用户接受现有固定环带为 idealised clamping baseline，完整夹具等效仍未验证。

真实 CAE 已生成五个独立材料变体并登记，非材料输入与历史基线一致。新版探索性 Loss/窗口及五点归一化设计已冻结；指定 Project Settings 为 PERSISTED，五个 Preflight/Dry-run 全部通过，Queue 未变，28 项合成测试通过。见 [run_017 总结](../run/run_017/summary.md) 与 [冻结批次](../run/run_017/artifacts/prepared_batch.json)。

位移校正方法、无损伤适用性和数值充分性继续保留不确定性。此准入仅用于首批探索性研究，不是正式反演或材料验证。旧 run_016 阻塞记录保留，新声明/许可的作用单独记录。未来需用户明确授权最多五个具体输入，串行逐个审核，无自动重试。

**保留验证隔离协议继续有效：独立数据保留验证，存在历史信息暴露。** 本轮没有读取/哈希隐藏拉伸源或派生内容；不宣称完全盲测。完成后停止，不自动求解、优化或解盲。


## 历史状态 — run_016（2026-10-23，Asia/Shanghai）

**BLOCKED（正式反演准入）；离线审计完成。** 真实 CAE/ODB 两项正式任务已完成并登记证据，MAIN 核验 14 项角色产物。名义试样尺寸相符，但固定夹持环带与实际下夹具接触未证明等效；SPT 力单位冲突仍未解决。合作方确认实际压头位移，校正细节仍待核验。Loss/窗口保持 PROVISIONAL，19 项合成测试通过。

公开资料与明确假设支持的新探索域及分阶段预算已定版，计算授权和执行仍为 0。当前不具备 DE/BO 首批新 Job 准入；解除阻塞后才考虑最多 5 个先导计算。run_014 单次求解授权已用完。见 [run_016 总结](../run/run_016/summary.md)。

**先读[保留验证隔离协议](../docs/Blind_Inversion_Protocol.md)。** 当前定义为“独立数据保留验证，存在历史信息暴露”；旧暴露审计保留。本轮未继续访问保留拉伸源或派生内容，后续独立审查需未接触者。完成后停止，不自动计算或解盲。


## 历史状态 — run_015（2026-10-23，Asia/Shanghai）

**WARNING（离线完成）：SPT数值核对、真实ODB/CAE交付和12项Loss合成测试已完成；正式反演未准入。** 候选实验曲线与既有FE仅作PROVISIONAL对照，力单位标签冲突、测点/零点/柔度、实际条件和FE数值充分性仍待核验。探索性参数域与48个新Job预算已冻结，当前执行授权和实际新增FE均0。

**必须先读[盲反演协议](../docs/Blind_Inversion_Protocol.md)。** 用户先追加保留资料审计，之后禁止访问并要求最终解盲验证；禁令前MAIN/ODB已读取，不能宣称完全盲测。禁止继续读取拉伸源及既有派生/混合报告，不使用其信息选择参数、Loss或预算。严格盲态未恢复，建议未接触者复核/执行；已有SPT证据保留。当前仅使用[run_015总结](../run/run_015/summary.md)和其中明确允许的SPT入口，不自动打开封存补充审计。新Solver、真实DE/BO和解盲均需后续明确授权。本轮完成后停止。

## 历史状态 — run_014（2026-10-21，Asia/Shanghai）

**WARNING（本轮完成）：Datacheck PASS，Full Analysis COMPLETED_WITH_WARNINGS，真实ODB提取PASS。** 唯一 `SPIO_R014_Q200_N010`，queue_id=`q_4c0358a918a7447d807d2f547d22c7b8`，授权task_id=`93322987-9489-47c1-908a-dd43e0736339`。用户一次GUI Start Queue后两阶段返回0，总耗时165秒，14CPU/0GPU、单次/零重试。真实ODB任务 `35b07ba1-22ad-48a7-b859-2d99199ed419` 已完成；MAIN收到消息并核验14项Hub证据和曲线差异。170点F–D末点力755.8151，较历史差−0.07782，最大曲线差13.5922（模型单位）；保存帧PEEQ最大0.69390<0.9。39次拒绝尝试、4条负特征值、2条过度畸变警告，以及native瞬时子进程身份缺口保留。科学状态NOT_EVALUATED，未实验验证；本次授权已用完，进一步求解需新授权，不自动进入下一Run。见 [run_014总结](../run/run_014/summary.md)。

## 历史状态 — run_013（2026-10-21，Asia/Shanghai）

**PASS（工程执行链路预检查）；可申请首次单次新Hollomon候选模型正向求解授权。** 严格按Project ID查询返回PERSISTED，无默认字段补齐；Abaqus命令、14 CPU、GPU关闭、Datacheck/Full开启及Auto shutdown关闭均已核实。候选INP哈希未变，修复版公开preflight/dry-run重新通过，Queue为空未变，未运行求解或datacheck。run_012的Settings阻塞已由 [新证据](../run/run_013/artifacts/run012_blocker_resolution.json) 解决；其原历史文件/结论全部保留。AgentHub已登记六项证据及解除阻塞消息。科学状态NOT_EVALUATED，入队及启动仍需明确授权。见 [run_013总结](../run/run_013/summary.md)。

## 历史状态 — run_012（2026-10-21，Asia/Shanghai）

**BLOCKED：官方preflight/dry-run实际通过，但目标Project Settings未保存到可核验文件。** Project/候选INP身份已核实，Abaqus命令存在；以用户明确给定的CPU14、GPU0、datacheck/full=true参数执行公开API，返回PREVIEW_READY/DRY_RUN_READY。参数来源为用户消息，非已读取Settings。Queue前后为空且不变，未Solver/datacheck/入队/自动关机。5项证据和结果消息已登记现有AgentHub。需目标Project runtime/settings.json存在并核对一致后才具备申请单次Solver授权的完整条件；材料科学有效性仍NOT_EVALUATED。见 [run_012总结](../run/run_012/summary.md)。

## 历史状态 — run_011（2026-10-21，Asia/Shanghai）

**PASS（限Project注册）；科研执行仍BLOCKED。** 已通过稳定版官方API把既有 `SP-InvOpt run_008 candidate preview` 注册到GUI同一用户的recent_projects，并用公开API确认ID和根目录。原因是run_008仅登记到仓库独立recent文件。Queue与Settings未变，没有创建重复Project或求解。已打开的Agent Command Console需关闭后重开以重新读取列表；未目视确认刷新。run_010的实际Settings/preflight/dry-run阻塞保持。见 [run_011总结](../run/run_011/summary.md)。

## 历史状态 — run_010（2026-10-21，Asia/Shanghai）

**BLOCKED：真实 MAIN→AgentHub→CAE→MAIN 已验证，AbqJobPilot Settings 缺失阻塞 preflight/dry-run。** 原SQLite正式任务 `a4b4805f-4989-4168-a54a-3bbf435b52a6` 已由真实CAE会话领取、登记产物并完成；MAIN回读产物哈希与持久完成消息。首次本地租约超时后按协议独立批准恢复，同一任务第2代完成。11项INP静态核验通过，科学状态NOT_EVALUATED。稳定版0.2.2 Project身份确认、Queue为空且未改；六项实际运行配置UNKNOWN。未Solver/datacheck/实际入队/修改旧模型/训练/commit/push；尚不具备单次Solver授权条件。见 [run_010总结](../run/run_010/summary.md)。

## 历史状态 — run_009（2026-10-21，Asia/Shanghai）

**WARNING：AgentHub 共享 SQLite、四角色身份范围与本地跨进程交接已验证；Codex 会话自动唤醒和科学求解未验证。** Run 008 的独立台账已保留并完成兼容迁移，新增 JSON CLI、AGENTHUB 维护身份、产物版本、失败诊断与任务持有者权限。MAIN→CAE→ODB→MAIN 的独立进程模拟交接通过；Run 008 的 8 项回归和 Run 009 的 8 项定向测试通过。模拟文件不是 Abaqus 输入或真实求解结果，科学状态为 `NOT_EVALUATED`。详见 [run_009 总结](../run/run_009/summary.md) 与 [CLI 指南](../agenthub_sp_invopt/CLI.md)。

AbqJobPilot v0.2.2 的公共 CLI 能力已复核；Settings 仍缺失，因此没有 preflight/dry-run、Queue 写入或 Solver 启动。Stage-5/AbqJobPilot 源码与生产台账、原始 CAE/ODB 保持未改；未 commit/push。完成本 Run 后停止。

## 历史状态 — run_008（2026-10-21，Asia/Shanghai）

**WARNING：SP-InvOpt 三角色协调与候选 INP 接入已实现；AbqJobPilot Settings 缺失，preflight/dry-run 尚未执行，物理验证仍未进行。** 独立 `agenthub_sp_invopt` 使用 SQLite，覆盖 MAIN/CAE/ODB 身份与会话、依赖任务、事务领取、租约/恢复、幂等任务与消息、持久收件箱/发件箱、任务级权限、证据哈希/来源及追加式审计链。独立本地进程轮询与单赢家并发领取已测试；没有实现或声称跨 Codex 会话自动通知，人工 Handoff 仍适用。

本地 AbqJobPilot 稳定版为 v0.2.2 / `0dfdb222`，独立 Project ID：`b87d2cd6-8519-4ac3-bae6-7eb989fb2dae`。公共 API 与 MCP 五工具清单已核验；通过 MCP 调用队列/历史列表、状态、输出定位，记录均为空或 UNKNOWN 且 Queue 哈希不变。当前全局与新 Project 的 Settings 文件均不存在；有效 CPU/GPU、Abaqus 命令及 datacheck/full-run 开关为 UNKNOWN，因此没有调用使用默认配置的 preflight 或 dry-run。实际写入 Queue、启动 Solver、恢复/重试均未授权且被 Hub action guard 拒绝。

唯一候选 Job `SPIO_R008_Q200_N010_Candidate` 位于独立工作目录，固定 E=210 GPa、ν=0.3、σy=200 MPa、n=0.1、pmax=0.9；Abaqus 2024 `inpParser` 语法解析通过。源为历史 Job-1 INP 的只读输入，CAE 数据库与该历史 INP 的一致性 UNKNOWN；候选模型仍是真总应变解释下、未经最终实验确认的材料模型。ODB 角色只读提取历史 Job-1 ODB 的181组 U2/RF2同步历史，源 ODB SHA-256 前后相同；该回归仅验证读取接口，**不是候选材料求解结果**。

非 Solver 验收和产物见 [run_008 总结](../run/run_008/summary.md)、[AbqJobPilot / MCP 结果](../run/run_008/artifacts/mcp_readonly_results.json)、[端到端交接](../run/run_008/artifacts/end_to_end_simulation.json) 与 [独立 CAE 验证交接](../run/run_008/artifacts/cae_verification_handoff.json)。完成当前授权后停止，不自动入队或运行 Solver。

## 历史状态 — run_007（2026-10-12，Asia/Shanghai）

**WARNING：候选Hollomon材料参数化已实现，文献测度和物理材料有效性未确认。** 固定E=210 GPa、ν=0.3，严格扣除当前弹性应变，固定应力单位换算，完成自适应插值和11项单元测试。回归样例覆盖p=0.9，35个点，独立采样误差约0.09504%，保守上界约0.09646%，满足0.1%数值目标。该范围依据既有ODB全部保存帧的积分点PEEQ加明确余量提出，不能保证未来参数或实验有效范围。

生成器标记为未获物理验证的候选实现。未修改Excel、CAE、INP，未运行Solver、创建/提交新Job或训练RL；未安装依赖，未commit/push。原有CAE修改和REC删除保留。详见 [run_007总结](../run/run_007/summary.md) 和 [生成器说明](../docs/Hollomon_Material_Generator.md)。当前指令完成后停止，不自动执行下一Run。

## 以下为历史状态记录

截至 2026-10-12（Asia/Shanghai），当前为 run_005 / Stage 2 准入只读审计；正式参数化求解尚未准入。研究项目名为 SP-InvOpt，仓库名保持 SMALL-PUNCH。

**状态：WARNING。现有 ODB 的真实 Punch RP 曲线提取已验证，模型物理输入与数值充分性仍未核验完毕。未宣告整体 PASS。**

run_005 已用 Abaqus 2024 自带 Python 3.10.5 只读打开 Sanity Job-1.odb，实际提取 `ASM_SPT.1` 的181点 U2/RF2；与同节点 Field 输出逐点一致。INP/ODB 网格、Step、RP链路和同目录日志相符，Job 正常结束。按向下压入取 d=−U2、F=−RF2，无插值、绝对值或2π附加系数；末点约0.0012和755.893，物理单位未确认，图与CSV使用模型单位。

Journal 已作文本顺序审计，确认初始自由UR3后来改为0，当前INP与ODB支持转动约束。JNL中的求解消息属于凌晨旧Job，不能代表晚间Job的完整操作历史；保存CAE与最终INP一致性仍NOT VERIFIED。TempTry作为独立历史比较：与Sanity输入哈希相同、ODB创建时间及哈希不同，U2/RF2及8项能量历史逐点一致；没有混用两组结果。

分层判定：**Level 1 Model Evidence WARNING；Level 2 ODB Extraction PASS（限模型单位内的读取与定向变换）；Level 3 Forward Reproducibility WARNING（有限历史重复证据）**。材料Plastic表的应变定义/单位、轴线U1约束、网格/增量敏感性和完整接触能量仍待确认。45次失败尝试中出现负特征值与畸变警告，最终收敛不解除这些风险；曲线局部陡增尚需解释。未运行新Solver、datacheck、Job、Journal replay、参数化、优化或RL；未修改模型或环境，未commit/push。完整交付见 [run_005总结](../run/run_005/summary.md)、[准入报告](../run/run_005/artifacts/forward_model_readiness.md) 和 [真实曲线](../run/run_005/artifacts/force_displacement.png)。下文为历史Run记录，旧“无模型/ODB”结论已被本次发现更新。

run_004 按用户指令确认默认研究 Python 仍为 `D:\XianLab\envs\conda\torch-gpu\python.exe`，与 AGENTS、启动文档及历史 Run 一致。普通 Python、NumPy/SciPy、Force–Displacement 绘图、DE/BO 与 RL 开发优先使用此解释器，所有 Python 执行命令须显式指定解释器。Abaqus CAE/ODB API 使用 Abaqus 2024 自带 Python，禁止用 Torch-GPU 导入 `odbAccess`；两类进程通过 JSON/CSV 交接。未创建或覆盖任何 IDE/项目环境配置，未改变已有解释器约定。

本轮实测 Python 3.11.13、8 个历史研究包和 SciPy DE API 可导入；`pip check` 返回 1：`pytest 9.1.1 requires iniconfig, which is not installed.` 已报告，未修复或安装依赖。BoTorch、GPyTorch、scikit-optimize、Optuna、bayesian-optimization 的分发元数据未检出；BO 具体工具选型及完整运行能力为 UNKNOWN。导入成功不代表 GPU、训练、优化或绘图端到端验证。默认解释器不可用时仍须 BLOCKED，不自动切换、创建环境或安装/升级/降级依赖。

本轮基线为 main / `a52be779f3b6ae9f830573764d5eed439df70b3b`，已有未跟踪目录 `CAE/Models/Sanity/`、`CAE/Models/TempTry/` 保留且未核验内容。因此下文 run_001 的模型可用性描述仅为历史审计，不据此判断当前目录中的模型。未调用 Abaqus、Solver、优化或 RL 训练，未 commit/push；本次仅记录并核验解释器选择。证据见 [run_004 总结](../run/run_004/summary.md) 和 [环境报告](../run/run_004/artifacts/environment.json)。

run_003 根据用户提供的项目启动文档和 README 设计备忘录重构双语主页：各约 200 行，首屏聚焦研究问题与真实状态，保留原创 SPT SVG 和两张 Mermaid 图，将完整本构/RL/MDP 定义移入双语 docs/Inverse_Identification 文档。增加文档导航、可执行轻量文档检查、防数据泄漏及独立验证说明。16 项文档检查通过；未进行真实 GitHub Mermaid/MathJax 渲染，科研阻塞不变。

本次发现 run_001/002 之后已有提交 `afdb19a4428b4e108204ebf35065dae3f2daeed7`（updated run 002）；开始时仅用户新加的启动文档未跟踪。启动文档中“run_002 尚无完成回报”是旧快照，以已存在的 run_002 完成记录为准。下述未提交/未推送描述仅指各历史 Run 当时的执行行为。run_003 未 commit/push，未修改用户启动文档或仓库外备忘录。

run_002 已编写实质一致的英文 README 与中文版，包含五层 Mermaid 架构、反演目标函数、RL 预算约束序贯搜索与 MDP、三个研究问题和四阶段路线图。没有实现算法、运行仿真或提出新实验结论。由于 run_001 遗留未提交改动与共享文档修改混合，本次不自动 commit，未 push；文档检查证据见 run_002。以下 run_001 事实保持有效，文件/环境检查不等于 CAE 合理性验证。

按补充要求新增 docs/figures 下原创 SPT 轴对称 SVG，已渲染并目视检查，双语主页共用；另加入 RL–Abaqus–奖励–策略更新 Mermaid 闭环，训练更新与部署推理分开。所有图为英文标注，不包含实验数据或已核验几何的暗示。

- 已建立 Agent 工作契约、研究概述、架构、本构契约、数据边界、文件通信与 Run 协议。
- 17 项轻量检查全部通过，包括原始资料完整性、目录/Run 协议、忽略规则、Markdown 本地链接及 Git 状态约束；研究未决项仍保留 WARNING。
- 5 个原始文件由 Materials/ 迁入 references_private/，迁移前后 SHA-256 一致，内容未修改；完整清单仅在忽略的本地审计区。
- 指定外部 Python 3.11.13 可用，8 个指定包均可导入。Abaqus 2024 release 查询及内置 Python 3.10.5 查询成功。
- 未安装依赖、未运行 Solver、未打开/修改 CAE、未训练或优化、未 commit/push。
- run_001 审计时只有公式/参考资料，无可审计 CAE/INP/ODB；run_005 已核验现有 INP/ODB，实验力–位移数据仍未确认。
- Excel 固定屈服应变偏移与通常的当前弹性应变扣除存在待澄清差异；文献与应变测度未确定。正式材料表生成和反演研究暂缓。
- Abaqus 许可证、CAE 启动和求解能力未测试；AbqJobPilot 六个接口全部 PLANNED / UNVERIFIED。

现有证据已支持基准 ODB 曲线提取，但不足以直接进入正式参数化求解或已验证的 FE 反演。Stage 2 准入审计已完成；参数化及后续优化/RL仍未启动。下一步先确认材料应变与单位、保存模型一致性和轴线/夹持意图，再另行授权独立工作目录中的受控重复计算及网格/增量敏感性验证。run_004的依赖缺失仍保留，未安装修复。本轮完成后停止，不自动执行run_006。

详见 [run_001 总结](../run/run_001/summary.md)、[run_002 总结](../run/run_002/summary.md)、[run_003 总结](../run/run_003/summary.md) 和 [CAE 审计](../docs/CAE_Model_Audit.md)。


## 最新更新 — run_006（2026-10-12，Asia/Shanghai）

当前最新 Run 为 **run_006 / Hollomon 数学与材料定义审计，WARNING**。本段更新此前 run_005 最新状态的历史快照。全部工作簿参数组的应力公式已通过独立数值核验，与文献塑性段一致；但在真总应变解释下，固定屈服应变偏移并不等于标准塑性应变转换。现有 INP 忠实保留派生列及其非恒定应力缩放，近屈服采样也造成独立插值偏差。三项差异已分别量化，模型未修改。

完整截图上下文、应力/应变测度和材料有效范围仍需确认。数学检查 PASS 不代表物理模型准入 PASS；正式材料参数化仍待明确契约。独立 A/B/C 诊断曲线、比较图和报告已保存在新 Run 私有审计区，不是已获准的生产材料表。源文件完整性验证通过；未调用 Abaqus、Solver、Job、优化、RL 或 commit/push，未变更解释器和依赖。参见 [run_006 总结](../run/run_006/summary.md)。本轮完成后停止，不自动进入下一 Run。
