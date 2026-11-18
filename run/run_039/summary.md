# run_039 — 20项 DOE 批量审计与优化准入

**WARNING / 19_OF_22_NUMERICALLY_SCOREABLE。** 原run_033的20项尝试中19项软件完成，D09原尝试中断、终态不明；未确认普通求解失败。D09独立run_038替代Job软件完成但有阻塞数值警告，其Loss为null。合并未重复执行的I01/I02，22个独立参数点中19个有冻结协议的探索性PROVISIONAL Loss，D07/D09/D10保持null。真实ODB Agent通过AgentHub完成提取，MAIN实际收取消息并独立重算19项。

最低已评估点D01：σy=152.308634 MPa，n=0.230662414，Loss=0.00050616408，RMSE=32.148 N；I08次之。五个Loss≤0.01的稀疏点在归一化参数上呈负相关（r=-0.940），提示补偿，不能证明连续谷地或唯一材料参数。BO/DE准入为**WARNING：仅适合另行授权的受限探索**，建议最多16个新增FE，先4 BO+4 DE审核，再决定余下4+4；本Run没有新增计算。

完整[MAIN报告](artifacts/private/main/REPORT.md)、[22点表](artifacts/private/main/evaluated_22_points.csv)、[原20项执行审计](artifacts/private/main/original_20_execution_audit.csv)、[参数Loss散点](artifacts/private/main/parameter_loss_scatter.png)、[低Loss区域](artifacts/private/main/low_loss_zoom.png)、[最佳F–D对照](artifacts/private/main/top_five_fd.png)、[全域与局部对比](artifacts/private/main/global_local_loss.png)及[Loss与数值成本](artifacts/private/main/loss_vs_runtime_cutback.png)均在Git忽略的私有证据区。历史run_025 BLOCKED、D09中断及封存拉伸数据禁读和既往暴露声明保留。完成后停止。
