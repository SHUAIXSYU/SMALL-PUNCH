# run_042 — BO/DE 先导批次真实结果

**WARNING / PILOT_COMPLETE_NO_BASELINE_IMPROVEMENT。** 8/8单次Datacheck+Full软件完成，真实ODB会话完成只读提取；5/8可按冻结Loss探索性评分。BO01、BO02、DE02因接受态反力回落或大应变警告保留null，无自动重试。MAIN独立复算5项结果，固定241点目标和原Loss未变。

BO新4次中2项可评分，最佳BO04：Loss=0.001890287691，σy=385.086544 MPa、n=0.0810010692。DE新4次中3项可评分，最佳DE03：Loss=0.07813127904，σy=585.733358 MPa、n=0.08。两支含共同起点的best-so-far均保持D01 Loss=0.0005061640799，改善0。BO/DE是一次batch及半代单种子先导，不能推导总体算法优越性。

建议暂停原BO4+DE4追加，先处理数值资格与参数补偿/不确定性；若需要新FE，另行冻结最多2个点级数值验证加4个识别设计的协议及授权。D01仅保留当前最佳探索性候选，尚不支持唯一材料识别或自动解盲。

完整[私有报告](artifacts/private/main/REPORT.md)、[8项数据](artifacts/private/main/eight_results.csv)、[预算曲线](artifacts/private/main/loss_budget_and_cost.png)、[参数散点](artifacts/private/main/parameter_loss_scatter.png)、[F–D对照](artifacts/private/main/best_fd_comparison.png)及[预测本构](artifacts/private/main/predicted_constitutive_curves.png)。8次已启动授权全部消耗；第二阶段额外8次未授权。本Run无新增求解、入队、重试或RL，历史BLOCKED与封存拉伸隔离声明保留，完成后停止。
