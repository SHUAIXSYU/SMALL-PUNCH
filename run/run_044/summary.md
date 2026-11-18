# run_044 — D01/I08 两项数值验证授权入队

**WARNING / TWO_VALIDATION_JOBS_QUEUED_AWAITING_MANUAL_START。** 第一阶段完成；当前只有两个获授权Job可执行，均QUEUED，尚未启动Datacheck或Solver。请用户在正确Project核对后手动点击一次 **Start Queue**。

Project：`E:\Projects\SMALL-PUNCH\agenthub_sp_invopt\abqjobpilot_project`；ID `b87d2cd6-8519-4ac3-bae6-7eb989fb2dae`。

| 顺序 | Job | queue_id | 实际回读状态 |
| --- | --- | --- | --- |
| 1 | `SPIO_R043_V_D01_M00125` | `q_dd23233452c544469eaebaff3fec2d8b` | QUEUED |
| 2 | `SPIO_R043_V_I08_M00125` | `q_e75bdad8123746279485618a7d6f32c9` | QUEUED |

## 当前检查与输入身份

新合法执行Run为run_044，原run_043准备和历史报告均保持不变。完整候选信息严格从run_043 prepared_batch.json读取，清单本身SHA与该Run输出记录一致；比较契约、比较实现、排序筛查实现及SPT目标hash同样核验。

两份完整INP hash：D01 `13e48fb2501a930f323b391c03e5f4e9ee6c3881959a837ca22cf94aab8939ca`，I08 `8b42fa6d30c4c3a7c47c3b732aafcd1fbd37b6588dfe5dff6b5a5aec7f647944`。每份相对各自原始源文件只进行已批准的0.0025→0.00125最大增量替换，其余每字节完全相同。初始增量0.001、总时间1、最小1e-12、最大增量数999999保持，材料/几何/网格/BC/接触/摩擦/加载/输出未变。独立工作目录为空，无覆盖、重复Queue或既有执行历史。

当前本机AbqJobPilot 0.2.2公开API确认Project身份及PERSISTED Settings；`D:\ABAQUS2024\Commands\abq2024.bat`存在，14CPU、0GPU、Datacheck=True、Full=True。2/2本轮Preflight与2/2 Dry-run通过后才开始公开API enqueue-only。未直接修改Queue JSON或Project DB；预览阶段保护文件hash未变，API入队即时检查Project DB未变，最终Settings仍一致。随后官方运行历史同步产生了来源runtime_json的两项QUEUED占位记录，started_at/completed_at均为空；History的run_count=1不能被当作已消耗一次真实FE尝试。最终Queue回读输入、工作目录、资源、模式、顺序、唯一queue_id和无started_at证据一致。

Runner所有权ABSENT、当前状态IDLE、运行恢复评估CLEAN、Solver进程CLEAR。旧run_033 D09独立目录的历史锁仍保留，通用计划中的旧锁警告已记录，不属于新输出目录、未清理或复用。当前无阻塞。

## 授权和停止点

MAIN经正式AgentHub接口登记本次用户明确授权、两输入hash、每项最多一次Datacheck+成功后一次Full、14CPU/0GPU、零自动重试和仅用户GUI启动方式。当前准备2、入队2、实际启动0、实际FE消耗0，额度仅保留给这两份冻结输入，不允许第三Job或替代/重试。

用户已接受AUTO_STOP_UNAVAILABLE批量风险：单项失败或警告后，Runner可能继续另一项；本机代码仍没有按求解结果可靠自动fail-stop，人工Stop After Current不能替代该能力。Codex没有点击GUI、调用Abaqus或启动后台求解程序。

两项统一完成后所需MAIN真实终态审计、真实ODB只读提取、MAIN五指标与Loss排序分析任务已在Hub登记，并以依赖约束隔离；目前未唤醒ODB会话，未宣称已完成求解或数值资格。只有用户通知运行结束后才开展第二阶段，严格使用run_043冻结协议，失败/不完整保留原始证据、不重试。

授权、每次API请求/响应、逐项回读、budget_ledger及最终完整Queue证据位于artifacts/private/。封存拉伸及其派生资料未访问，历史信息暴露和BLOCKED结论保留；无额外BO/DE、RL或Git提交。现在停止，等待用户GUI手动Start Queue。
