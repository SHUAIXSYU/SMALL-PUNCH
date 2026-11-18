# run_029 — 中心点进一步增量细化真实结果审核

**WARNING / PASS_CENTER_ADJACENT_REFINEMENT_ONLY。** 用户在 GUI 启动的唯一 Job `SPIO_R027_CTR_M0025` 已完成 Datacheck 与 Full Analysis；真实 ODB Agent 完成只读提取，MAIN 独立按 run_027 求解前冻结的协议审核。此结论仅限 V01 与新候选的相邻增量设置比较。

| 新候选对 V01 | 实测 | 冻结上限 | 结果 |
| --- | ---: | ---: | --- |
| F–D RMSE | 0.651090 N | 2 N | PASS |
| 最大绝对差 | 4.396976 N（0.775 mm） | 7.1445 N | PASS |
| 最大正则相对差 | 1.851343% | 5% | PASS |
| 绝对 Loss 变化 | 0.00004710218 | 0.00065 | PASS |
| 最大保存帧 PEEQ 差 | 0.0009343624 | 0.02 | PASS |

新候选 Loss 为 0.0482878153，V01 为 0.0483349174。443 次接受增量、19 次拒绝尝试；V01 分别为 273、26。1.10–1.16 mm 的 20 个已接受帧内，node 23 约在 1.126 mm 首见正 CPRESS，随后局部压力与载荷同步上升；这属于相关证据，不能确定唯一成因。接受状态仍有一条零力矩提示，类别和次数未较 V01 增加；负特征值、畸变和大应变标题发生在被拒试算中。

辅助比较显示 run_014 对新候选的 RMSE 4.20435 N、最大差 20.15764 N，较 run_014 对 V01 的 3.99878 N、19.55820 N 略增。因此 **run_025 对 run_014→V01 的历史 BLOCKED 结论保持不变**。本次也不验证四扰动点 Jacobian、网格收敛或实验本构。

完整身份、收敛、接触和科研边界见[私有 MAIN 报告](artifacts/private/main_report.md)、[结构化审核](artifacts/private/main_review.json)、[真实 ODB 报告](artifacts/private/odb/REPORT.md)、[三曲线图](artifacts/private/comparison/full_comparison.png)与[局部图](artifacts/private/comparison/focus_110_116.png)。私有曲线和恢复记录保存在 Git 忽略区。

ODB AgentHub 第一代短租约过期后，MAIN 在确认该真实 ODB 会话停止、产物及源哈希稳定后，批准任务级恢复；ODB 第 2 代只登记已有 35 件产物并回传，未重新提取或求解。MAIN 核验 AgentHub 审计链与会话消息。无新增 Job、Solver、Datacheck、重试、V02、DE/BO/RL、封存拉伸访问或 commit/push；完成后停止。
