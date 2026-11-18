# run_027 — 单一中心点进一步增量细化准备

**状态：WARNING（离线准备完成，数值资格待求解）。** run_025 的 `BLOCKED_V01_NUMERICAL_QUALIFICATION` 原结论不变。无入队、Datacheck 或 Solver；V02 仍不可执行。

## 唯一输入与真实 CAE 交接

MAIN 通过 AgentHub 将任务 `551d73d5-ae9b-4ace-a9f6-30562b6e17a0` 交给真实独立 CAE Codex 会话。CAE 领取、生成、核对、登记证据并回传完成消息；MAIN 会话已实际领取该消息。源 V01 INP：`run/run_023/artifacts/candidates/SPIO_R023_V01_CTR/SPIO_R023_V01_CTR.inp`，SHA-256 `14006d69c15e6fd4be021b889964e5add51e724d52fd03ff817b0f80b747c2ff`。候选 Job `SPIO_R027_CTR_M0025`：`run/run_027/artifacts/candidates/SPIO_R027_CTR_M0025/SPIO_R027_CTR_M0025.inp`，完整 SHA-256 `dae9345bc60973c27edec498dfbd27f269e1f5bbe151316918862954faac40c9`；工作目录 `run/run_027/artifacts/solver/SPIO_R027_CTR_M0025` 当前为空。独立逐字节复核证明仅第 1468 行 `*Static` 的最大增量 `0.005 → 0.0025`，其余字节完全一致，无 INCLUDE 或外部模型引用。材料参数仍为 σy=200 MPa、n=0.1、E=210 GPa、ν=0.3；初始增量0.001，总时间1，最小增量1e-12，最大增量次数999999。

## 求解前冻结比较协议

`run027-adjacent-refinement-v1`，SHA-256 `e189ab1551f775f085fc0208e0550784db85fa3b258b6164db1f8a20c148d42a`。主要比较新候选与 V01；run_014 仅辅助观察趋势。固定 `run017-exploratory-fd-v1`、0–1.2 mm、241 个实验位移点、`u=-U2`、`F=-RF2`、线性插值、不外推、不平滑、不删点、不平移零点或再次柔度校正。预设工程门槛：RMSE≤2 N，最大绝对差≤7.1445 N，最大正则相对差≤5%（分母下限71.445 N），绝对 Loss 差≤0.00065，最大保存帧 PEEQ 差≤0.02。先核查 Job/ODB 身份、完整窗口、材料表覆盖及已接受帧警告。局部 1.10–1.16 mm 原始接受帧、节点23及拓扑相邻接触区域 CPRESS/COPEN、cutback/接触事件只作诊断，不替代全窗口门槛。COPEN 哨兵或缺失值不当作实际开口。

直接复用已测试比较实现 `run/run_023/artifacts/compare_validation.py`（SHA-256 `0a8e9d70716385292153613d8ca823f956b6142c2acaa67e8903fa2565a82a36`）和 Loss 实现 `inverse/fd_loss.py`（SHA-256 `48d8d900f9eb453bdf1c896fea734c589ca8ab22d47e9dd98b165353ee794fb0`）。12 项单元测试通过；V01 自比较为零差；原 run_014 对 V01 的 RMSE 3.998775 N、最大差19.558201 N 得以复现。这些测试均未评价新候选的数值结果。

## AbqJobPilot 只读预览

本机稳定版 0.2.2，正式 Project `b87d2cd6-8519-4ac3-bae6-7eb989fb2dae`。严格 Settings=`PERSISTED`，Abaqus 2024 命令文件存在，14 CPU、0 GPU、Datacheck 和 Full Analysis 开启。公开 API `preflight`=`PREVIEW_READY`，`enqueue(dry_run=True)`=`DRY_RUN_READY`；Project/Queue/Settings/历史记录在调用前后不变。Runner owner=`ABSENT`、recovery=`CLEAN`，新工作目录无冲突。预览不等于 Abaqus 语法、许可证或收敛检查；无 queue_id、无新 ODB。

## 停止与后续授权

本 Run 到候选准备即止。申请仅此一个新 Job 时，须明确绑定候选完整 SHA、Job 名、Project ID、工作目录、14 CPU/0 GPU、单次 Datacheck+Full Analysis、零自动重试，并重新检查 Queue/Runner/输出冲突；用户负责 GUI 手动 Start Queue。未取得新授权前不得入队或求解。V02 的未使用额度不得转给本候选。未来若该相邻细化通过，仅可判定本中心点增量细化；使用新设置优化须单独冻结数值契约，历史粗设置结果须标识精度来源。

证据入口：`artifacts/prepared_candidate.json`、`artifacts/cae_candidate_manifest.json`、`artifacts/comparison_contract.json`、`artifacts/comparison_test_result.json`、`artifacts/preview_result.json`；字节、Settings、Queue 和 CAE 会话证据在 Git 忽略的 `artifacts/private/`。
