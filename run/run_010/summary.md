# run_010 — Real Agent Integration & Preflight

状态：BLOCKED。真实 MAIN → AgentHub → CAE → AgentHub → MAIN 交付已完成；候选 INP 静态核验通过。AbqJobPilot 实际 Settings 缺失，preflight/dry-run 未执行，不具备单次 Solver 授权条件。

## 真实任务与证据

- task_id：`a4b4805f-4989-4168-a54a-3bbf435b52a6`。
- CAE Codex chat：`01a15d5e-a3ad-75f1-b53c-ac6a12c21c48`；真实 Agent：`CAE:cae-codex-20261021-632ffd48`；session：`aa78d383-febb-4b7e-99d5-2a9665e9ab6c`。
- 沿用原 SQLite，没有重建数据库。MAIN 正式创建任务并批准 verify_inp，通过平台向已有 CAE chat 发送明确交付提示。CAE 在其实际执行回合中领取任务、核验和登记；MAIN 未启动模拟 CAE worker。
- 首次租约30秒到期，CAE停止并发送诊断。平台确认其回合 completed/idle 后，MAIN 单独批准本地 Hub recover_retry 并恢复原任务。真实 CAE 第2次领取并完成，未涉及 AbqJobPilot/求解重试。
- MAIN 已收到该任务的持久完成消息；登记产物 SHA-256 均回读验证通过，审计链有效。见 [真实交接证据](artifacts/real_handoff.json) 与 [平台完成凭证](checkpoints/cae_completed.json)。
- 此结果证明本次授权的平台通知加真实会话主动领取，不代表 Hub 已部署后台自动唤醒服务。

## INP 结果

候选 `SPIO_R008_Q200_N010_Candidate.inp` SHA-256 `fa2de5d73a28536c1c07cd22072d2a24c1ae988c569127d728931c583457f05a` 与 run_008/task 一致。11项静态检查通过：E=210 GPa、ν=0.3、σy=200 MPa、n=0.1、pmax=0.9，35行表与现有 Hollomon 生成器完全一致，源 INP 除候选材料表和说明注释外可重建一致。保留首次检查脚本边界错误报告；修正后通过，未修改候选。当前 CAE 数据库与历史 INP 等价性仍 UNKNOWN；本构仍为候选真总应变解释，没有实验/物理验证。

## AbqJobPilot

稳定版0.2.2，HEAD `0dfdb22205535c88d3ef068d895c15b6a1ab051b`，源码工作树干净。复用 Project `b87d2cd6-8519-4ac3-bae6-7eb989fb2dae`；公开 API show_project、capabilities、Queue/History和输出定位均已读取。Project/global/legacy Settings 文件不存在，六项真实资源和阶段配置 UNKNOWN。源码默认值只作为来源审计记录，没有作为用户配置使用。

公开 API preflight 与 enqueue(dry_run=True) 的签名和实现已检查，但因缺少真实 Settings 均 BLOCKED/未执行。另观察到0.2.2命令预览读取 config.ABAQUS_CMD，且总是展示两个阶段模板，不能把它当成 Project Settings 或实际运行阶段的证据。项目/队列/用户 recent registry 的哈希前后相同，Queue为空。

## 交付与后续条件

新增 Run 010 协调/审计脚本、真实 CAE报告、台账事件和收件凭证，更新Run索引与项目状态。旧CAE/INP/ODB、外部稳定版源码均未修改；未 Solver/datacheck/实际入队/RL/commit/push。

单次 Solver 授权条件尚不满足。下一步需提供并核验本 Project 的实际 Abaqus 命令、CPU/GPU、datacheck/full-run Settings，并在相同 INP hash 上通过已授权的公开 preflight/dry-run；实际入队和启动仍须独立明确授权。Run 010到此停止。
