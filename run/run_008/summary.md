# run_008 — SP-InvOpt AgentHub / AbqJobPilot 协作引导

**状态：WARNING。** 项目内三角色 AgentHub、候选 INP、只读 ODB 接口检查和 AbqJobPilot v0.2.2 的 MCP 只读连接已实现并运行。真实 Settings 文件缺失，故 AbqJobPilot preflight/dry-run 未运行；没有写入 Queue、启动 datacheck/Solver 或恢复/重试。候选模型没有获得实验或新求解验证。

## 起始状态与保留边界

- 初始 Git 为 `main` / `e87aadc9f7074fc4bc127c9ae03afbe9081dabae`，origin 为 SMALL-PUNCH。既存 CAE 修改、REC 删除、run_007 及其他未提交/未跟踪更改均保留；未 commit/push。
- Stable AbqJobPilot checkout 起始为干净 `main` / `0dfdb22205535c88d3ef068d895c15b6a1ab051b`，版本 `0.2.2`。没有修改其源码、Project/Queue/Settings、recent-project registry 或用户配置。五工具的 MCP stdio 以只读/预览方式连接。
- Stage-5 AgentHub 是非 Git 工程目录。只读其 AGENTS、README、协议、现行 Release 记录和 source adapter；未打开或更改 Stage-5 SQLite、生产请求/响应、Project Queue 或源码。
- run_008 开始后出现空的 `run/run_009/artifacts/` 与 `checkpoints/` 目录。该未登记目录不是本任务创建，未写入、复用或删除；需维护者另行确认其归属。
- 历史 `Job-1.inp` SHA-256 为 `b2aac48a…5763305cc`，读取/生成前后保持；历史 ODB 的读取前后 SHA-256 均为 `612bdc14…709b3d8f`。用户已有的 CAE 数据库和 REC 删除没有被本 Run 操作。

## AgentHub 实现

新增 [独立 AgentHub](../../agenthub_sp_invopt/README.md)，SQLite 位于 Git 忽略的 `agenthub_sp_invopt/runtime/sp_invopt.sqlite3`。实现使用 Python 标准库，参考现有 Stage-5 AgentHub 已验证的 SQLite `BEGIN IMMEDIATE`、单赢家 claim、有限 lease、heartbeat、明确恢复、幂等键、持久 INBOX/OUTBOX、任务级审批、SHA-256 来源证据和哈希链事件。没有连接 Stage-5 数据库。

固定角色为 MAIN、CAE、ODB，分开保存执行状态、证据状态和科学状态；任务依赖只在父任务完成后可领取。会话绑定 `agent_id` 与 `session_id`；`poll.py` 是有限轮询的独立本地进程，测试到重复/并发 claim 只有一方成功。相同任务/消息幂等键和相同内容返回原记录，异内容冲突。过期 lease 进入 `RECOVERY_REQUIRED`，需要 MAIN 的 `recover_retry` 审批和明确 worker 已停止确认。生成、验证、入队、启动和恢复各有独立审批；本 Run 没有 Queue/solver executor，入队/启动 action guard 在本轮拒绝执行。

消息落库和独立 Python 进程收到消息/领取任务已验证。**这不代表另一 Codex 对话已收到通知。** 未实现跨 Codex 会话自动唤醒/投递；人工 Handoff 仍是可靠边界。

角色说明见 [STARTUP.md](../../agenthub_sp_invopt/STARTUP.md)，字段、轮询、租约、审批和证据说明见 [protocol.md](../../agenthub_sp_invopt/protocol.md)。

## 端到端模拟

1. MAIN 在独立账本创建 CAE 输入任务并写入 task-scoped `generate_inp` 批准。
2. CAE 独立进程轮询、领取任务、登记唯一候选 Job 和候选文件哈希。
3. 新 CAE 验证任务在依赖完成后由另一个 CAE 进程领取；核验候选材料行、唯一 Job 名、工作目录和 Abaqus 输入解析证据。
4. 独立 AbqJobPilot formal Project 已用 v0.2.2 公共 API 创建，Project ID `b87d2cd6-8519-4ac3-bae6-7eb989fb2dae`。Project 位于仓库的 `agenthub_sp_invopt/abqjobpilot_project/`，单独 Queue 为空。
5. ODB 进程领取依赖任务，以 Abaqus 2024 Python `openOdb(readOnly=True)` 读取原有 Sanity `Job-1.odb`：`Step_Punch_Displacement` / `Node ASM_SPT.1` 的 U2、RF2 各181个同步样本；SHA-256 前后一致。该证据只验证读取接口，不是新候选的求解结果。
6. MAIN 的真实本地进程轮询收到 CAE/ODB 结构化 inbox 结果。Hub 有3个已完成任务，审计 hash chain 校验通过；详细数据见 [端到端交接](artifacts/end_to_end_simulation.json)、[CAE 验证与 MAIN 收件凭证](artifacts/cae_verification_handoff.json)、[Hub 最终状态](artifacts/hub_state.json) 和 [最终核验](artifacts/final_validation.json)。

## 候选材料与 AbqJobPilot 核验

- 候选 Job 名 `SPIO_R008_Q200_N010_Candidate`，目录与 INP 同名且相互独立。参数为 E=210 GPa、ν=0.3、σy=200 MPa、n=0.1、塑性应变范围至0.9；35行候选 *Plastic 表由 `inverse/hollomon.py` 生成，输出 SHA-256 `fa2de5d7…3457f05a`。
- 候选 INP 从历史 Job-1 INP 只读取得几何/边界等其余文本，仅替换 `Q200N01 *Plastic` 区块。生成来源哈希、处理方法和项目内使用边界见 Git 忽略的 `artifacts/private/candidate_source_audit.json`。历史 INP 是否与当前已修改的 CAE 数据库一致仍为 UNKNOWN；不声称候选物理正确。
- 使用 Abaqus 2024 的 `inpParser.InputFile.parse()` 语法解析通过；这不是 datacheck 或物理验证。Abaqus Python 直接启动时因缺少 `ABA_PATH` 变量而失败，改由已安装 `abq2024.bat python` 包装器后执行成功。失败过程保存在私有审计目录。
- 真实配置文件在 AbqJobPilot 全局安装 runtime、新 Project runtime 和已有 Default Study Project 中均未找到。源码代码默认观察到的命令、CPU/GPU 和 datacheck/full 值不是本机已确认 Settings；因此没有使用它们。具体本地路径与环境记录位于忽略私有审计文件 `artifacts/private/environment_and_settings.json`。
- MCP SDK 2.3.0 连上稳定版五工具 `abq_preflight`、`abq_list_jobs`、`abq_job_status`、`abq_locate_outputs`、`abq_prepare_enqueue`。实际调用 Queue/History 列表、状态及输出定位，project Queue 哈希前后一致。候选 Job 显示 UNKNOWN/未登记，预期 ODB/STA/MSG/DAT/LOG/LCK 均不存在。Settings 依赖的 preflight、dry-run 预览工具没有调用。
- 探测过的现有 Project manifest 未发现同名 SP-InvOpt Project；Stage-5 数据仅查看 Project manifest，两个 AbqJobPilot 开发版 Project 按其本地规则跳过。

## 验证

- [AgentHub 测试](artifacts/hub_tests_final.txt)：8项通过，覆盖任务/消息/证据幂等、并发单赢家、租约恢复、伪造身份/跨角色证据拒绝、不同审批隔离和本地进程轮询领取。
- [候选/交付测试](artifacts/candidate_tests_final.txt)：3项通过，覆盖唯一 INP/Job 目录、材料表与来源哈希、历史 ODB 非候选结果语义、Project Queue 和 parser/MCP 边界。
- [Abaqus 输入语法解析](artifacts/candidate_inp_parse.json)：PASS_ABAQUS_INPUT_PARSE。范围仅限格式解析。
- [MCP 连接记录](artifacts/mcp_readonly_results.json)：五工具发现成功；四类只读调用完成；Queue 未变化。未调用 preflight/dry-run。
- 没有运行 Solver、datacheck、RL、优化或训练；没有复制/迁移 ODB 或 CAE，没有改动 Stage-5/AbqJobPilot 源码，没有提交 Git。

早期 MCP harness、Hub 单测和 Abaqus parser 的接口尝试曾失败；修正 response 字段、连接关闭/测试夹具、Abaqus 环境包装和 cwd/output path 后，最终上述测试通过。私有日志保留可用的 MCP/parser/CAE 重试记录。历史 ODB 的 CAE/ODB 完整设置物理有效性和材料实验验证仍未执行。

## 下一次单次 Solver 验证的最小授权

先恢复/确认本机 AbqJobPilot Settings，并核对 `abaqus_cmd`、CPU/GPU、datacheck 与 full-run 开关。确认前不要用代码默认值。随后单独授权本 INP/唯一 Job 的 AbqJobPilot preflight 和 dry-run（不写 Queue）；审核预览后，再另行明确授权一次 Queue 元数据写入。当前稳定 API 声明不提供 Solver start，真正启动需操作 AbqJobPilot QueueRunner 的显式 Start Queue；必须再单独确认仅运行此一个 Job 及其已核实资源配置。此次最小方案不包含恢复、重试、第二个 Job 或参数搜索；任一失败先保留证据并停止。

本 Run 到此完成，等待下一条明确指令。
