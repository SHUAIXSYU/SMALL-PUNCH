# run_017 — First Constitutive Sensitivity Study Preparation

**WARNING（离线准备完成）；具备申请首批最多五个探索性敏感性 Job 的条件。当前授权数=0、入队数=0、Solver/Datacheck 执行数=0。**

## 实际完成与准入

- 新的合作方实验元数据已登记；载荷单位冲突由来源方澄清，保留原冲突与 run_016 历史结论。
- 真实 CAE 会话领取并完成正式任务，MAIN 核验 19 项 Hub 证据；名义几何一致。固定环带按用户许可作为 idealised clamping baseline，不宣称完整夹具等效。
- 生成五个独立材料变体、参数 JSON、唯一 Job 名与独立工作目录。除 Plastic 表和候选注释外，与原输入字节一致；旧模型未改。
- 新版 `run017-exploratory-fd-v1` 冻结实验比较契约，重新计算既有参考。实验数值保持；不二次校正、不按候选调整窗口、零点或尺度。仍不构成正式材料反演结论。
- 指定 Project 的实际 Settings 返回 PERSISTED，14 CPU/0 GPU、Datacheck 与 Full 开启、Auto shutdown 关闭；五个 Preflight/Dry-run 全部通过。Queue、Settings 与 Project DB 未变。
- 28 项合成测试通过（19 Loss、9 局部敏感性）；五个 INP 静态复核通过。未执行 Abaqus 语法/datacheck 或未来结果提取。

## 五点设计

x=ln(σ_y/150)/ln(1000/150)，y=(n−0.02)/0.48；中心 (0.5,0.5)，各方向扰动 ±0.2。中心不是真实材料参数。

| 点 | σ_y / MPa | n | Job |
| --- | ---: | ---: | --- |
| P01 | 387.298335 | 0.260 | SPIO_R017_P01_CTR |
| P02 | 265.010988 | 0.260 | SPIO_R017_P02_SYM |
| P03 | 566.014266 | 0.260 | SPIO_R017_P03_SYP |
| P04 | 387.298335 | 0.164 | SPIO_R017_P04_NM |
| P05 | 387.298335 | 0.356 | SPIO_R017_P05_NP |

使用冻结 JSON 的完整精度；E=210 GPa、ν=0.3，真总应变候选 Hollomon、塑性表覆盖至0.9。未来 PEEQ 是否充分覆盖未知。

## 证据与修改

- [完整私有报告](artifacts/private/main_preparation_report.md)
- [冻结批次/完整输入哈希](artifacts/prepared_batch.json)
- [CAE 候选清单](artifacts/cae_candidate_manifest.json)
- [逐点公开 API 预览](artifacts/batch_preview_result.json)
- [Loss 契约身份](artifacts/loss_contract_identity.json)
- [ODB、敏感性、成本与停止协议](artifacts/odb_analysis_protocol.md)
- [合成测试](artifacts/test_results.json)
- [旧阻塞的新证据说明](artifacts/run016_resolution_by_new_evidence.json)
- [AgentHub 登记](artifacts/agenthub_receipt.json)
- [证据清单](artifacts/manifest.json)

全部新分析/候选文件在本 Run；更新 Run 索引及项目状态。私有实验曲线/来源审计在 Git 忽略区，未来 Solver 输出目录也已忽略。14 个明确基线文件哈希保持，未改外部项目/环境、原始实验/模型，不 commit/push。

## 剩余限制与下一步

位移校正方法、夹具完整接触/预紧/柔度、摩擦、试验速度/温度、无损伤窗口、数值充分性与材料模型科学有效性仍有不确定性。首次是局部敏感性研究，不能证明全局唯一性或直接启动正式 DE/BO。

按历史165秒机械外推，五个约13.75分钟、3.21分配核时，实际成本待测。建议未来串行、一次只入队一个、逐个审核，失败或重要警告停批；每个最多一次，零自动重试。获得授权后仍需在执行时复核身份、Settings、空输出与 Runner 状态。

研究继续表述为“独立数据保留验证，存在历史信息暴露”；未重新读取保留拉伸源及派生内容。完成本轮后停止，等待用户正式授权；不自动创建下一 Run 或启动计算。
