# run_030 — 16次探索性反演离线准备

**WARNING / READY_TO_REQUEST_STAGE_A_WITH_GATES。** 数值契约 `run030-standard-m0025-hollomon-v1` 冻结；run_027 中心相邻细化通过仅支持这个中心的数值设置选择，不推定全参数域稳定。run_025 历史 BLOCKED 保留。没有新入队、Datacheck、Solver 或优化执行。

## 冻结设计与模型

8点中4点按归一化参数域分层覆盖全域，4点围绕既有 SPT 低 Loss 区域；序列交错，先评 I01–I04。范围 σy=150–1000 MPa、n=0.02–0.50 是工程探索假设，E=210 GPa、ν=0.3。数值设置：Abaqus/Standard、初始0.001、最大0.0025、最小1e-12、总时间1、最多999999增量；14 CPU、0 GPU、Datacheck+Full。几何、网格、接触、BC、位移加载、输出及候选 Hollomon 解释沿用源模型。

| 点 | 区域 | Job | σy (MPa) | n |
| --- | --- | --- | ---: | ---: |
| I01 | GLOBAL | `SPIO_R030_I01_G` | 190.142785434 | 0.440000 |
| I02 | LOCAL | `SPIO_R030_I02_L` | 188.347694261 | 0.116000 |
| I03 | GLOBAL | `SPIO_R030_I03_G` | 305.532234950 | 0.200000 |
| I04 | LOCAL | `SPIO_R030_I04_L` | 211.054604981 | 0.173600 |
| I05 | GLOBAL | `SPIO_R030_I05_G` | 490.946560924 | 0.320000 |
| I06 | LOCAL | `SPIO_R030_I06_L` | 236.499026222 | 0.096800 |
| I07 | GLOBAL | `SPIO_R030_I07_G` | 788.880838459 | 0.080000 |
| I08 | LOCAL | `SPIO_R030_I08_L` | 265.010988075 | 0.154400 |

完整精度、8个输入完整 SHA-256、路径与工作目录见[冻结清单](artifacts/prepared_batch.json)。真实 CAE 会话领取、完成任务，并向 MAIN 回传；MAIN 核验27项 AgentHub 产物哈希及完成消息。8份 INP 的非材料字节与 run_027 源完全相同，塑性表覆盖0–0.9且插值误差界≤0.001，8个独立工作目录为空。

## Loss、预检查与预算

Loss继续用 `run017-exploratory-fd-v1`：私有 SPT 339点源中的0–1.2 mm、241点，F_ref=1428.9 N，等权归一化均方残差，线性插值且无外推/零点平移/二次校正。目标、配置及实现 SHA 再核验一致；不读取封存拉伸数据。

正式 AbqJobPilot 0.2.2 Project Settings=`PERSISTED`，Abaqus 2024命令存在，14 CPU/0 GPU、两阶段开启。CAE及MAIN分别通过8/8公开API Preflight、8/8 dry-run；两次预览证据显示 Queue/Project/Settings/History未改变，且无新queue_id或Solver。预览不代表 Abaqus 语法、许可证或收敛已通过。

总新增 FE 拟定上限16：共享初始8 + BO序贯4 + DE半代先导4。两算法只共享同一8点，后续各只看自身新增结果；单种子小预算不比较算法优劣。首4点完成后人工检查成功样本、Loss、补偿和警告，再决定后4点；8点完成后才审议BO/DE。任何失败、不完整覆盖、材料越表、严重接受态警告或不明运行状态都停止后续提交，Loss=null，不自动重试。详见[完整协议](artifacts/pilot_protocol.md)与[未来ODB回传格式](artifacts/odb_result_protocol.json)。

中心点实测253秒/Job；规划4–20分钟/Job，仅作为范围估计。首8点32–160分钟，全部16点64–320分钟（不含等待/人工审核，不能视为保证上限）。具备**申请**最多8项首批探索性求解授权的离线工程条件，但建议先授权并逐项审核 I01–I04，再决定后四项；本轮实际授权、入队及新计算均为零。固定夹持理想化、接触/警告、仪器校正细节、参数耦合与数值域外推风险仍在，不能宣称材料本构或全局参数已验证。

证据：[MAIN独立审核](artifacts/private/main_verification.json)、[真实CAE回传验收](artifacts/private/main_cae_acceptance.json)、[CAE报告](artifacts/private/cae/REPORT.md)、[预算契约](artifacts/budget_protocol.json)。六项离线契约测试通过。完成后停止，不自动进入新Run。
