# run_043 — 低Loss可识别性与数值资格准备

**WARNING / READY_TO_REQUEST_TWO_POINT_REFINEMENT。** D01/I08已有输入、ODB、单次执行与数值证据复核通过。两者Loss接近但残差形状不同：D01整体偏低约29.1 N，I08偏高约25.2 N；两条FE曲线互比RMSE57.71 N。预测真总应变1%处应力约278.97/364.81 MPa，差85.83 MPa。现有24个有效点支持多个竞争候选及补偿趋势，尚不能确定唯一材料本构。

真实CAE已准备两个独立候选，仅最大增量0.0025→0.00125，其余逐字节不变；2/2 Preflight、2/2 Dry-run通过。原五项工程判据及独立Loss排序敏感性筛查已冻结（基线间隔5.572786901e-05），比较12项与新增排序4项测试通过。当前0入队、0Solver/Datacheck。

建议申请这两项定向验证，通过后优先研究补偿谷地/不确定性；不直接恢复BO/DE。可冻结探索性候选集合，最终本构及独立拉伸验证尚待数值资格和明确解盲授权。完整[分析报告](artifacts/private/main/REPORT.md)、[F–D与残差](artifacts/private/main/fd_differences_residuals.png)、[预测真总应变本构](artifacts/private/main/predicted_true_total_curves.png)、[Abaqus塑性表](artifacts/private/main/abaqus_plastic_curves.png)、[冻结比较协议](artifacts/comparison_contract.json)及[候选清单](artifacts/prepared_batch.json)。封存拉伸禁读和历史暴露声明保持，完成后停止。
