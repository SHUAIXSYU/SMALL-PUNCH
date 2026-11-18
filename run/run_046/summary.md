# run_046 — 候选本构冻结与独立验证准备

**WARNING / FROZEN_AWAITING_EXPLICIT_UNBLIND_AUTHORIZATION。** 已结束当前探索性优化阶段，冻结D01当前最佳已评估候选和I08竞争性替代候选。完整精度参数、最新探索性SPT Loss、点级数值资格PASS、两个数值契约来源、目标身份及限制均已保存。

每条真总应变曲线0–0.9含10,803点，Abaqus塑性表0–0.9分别51/40点，与已求解INP材料行逐值一致；固定E210GPa、nu0.3，保留候选真总应变解释。真总应变1%时应力约278.97/364.81MPa，相差85.83MPa；两曲线不是置信区间。

独立验证已预注册：真实量/工程量与总/塑性应变区分、颈缩前适用条件、批次/材料状态门控、固定主窗0.002–0.10真总应变981点、预设子区间、绝对/相对误差和两候选排序。覆盖不足则主评分null，不缩窗。初始sigma_y不等于Rp0.2；仅另给固定E210统一偏移诊断。没有实验容差依据，不杜撰物理PASS阈值。

11项合成测试通过，输出和ZIP内每项SHA核验通过。见[冻结收据](artifacts/freeze_receipt.json)、[完整私有包](artifacts/private/SP_InvOpt_run046_frozen_candidates.zip)、[冻结结果](artifacts/private/freeze/frozen_inversion_results.json)、[验证协议](artifacts/private/freeze/independent_validation_protocol.md)、[预测曲线](artifacts/private/freeze/candidate_constitutive_comparison.png)。原始SPT数据仅绑定身份未修改，封存拉伸及派生结果未访问。

可以申请明确解盲授权，并优先安排未接触保留数据的复核人员。此处就绪不等于已经解盲、已确认同材或已经完成物理验证；历史run015信息暴露、run025 BLOCKED和D09历史成本/次数UNKNOWN保留。没有Solver/datacheck/入队/重试/新优化/RL或Git提交。本Run完成后停止。
