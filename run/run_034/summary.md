# run_034 — 20项 DOE 实际结果审计

**WARNING / MAIN_REVIEW_COMPLETE_WITH_THREE_UNSCORED。** AbqJobPilot 公开证据显示20项均已尝试一次；19项求解完成，D09 为 UNKNOWN_INTERRUPTED、Full 终态不明且 `.lck` 存在。真实 ODB Agent 只读提取19项；17项按冻结 Loss 评分，D07/D10/D09 保持 null。

最低已评估点 D01：σy=152.308634 MPa，n=0.230662414，探索性 Loss=0.0005061640799、RMSE=32.1475 N。五个 Loss≤0.01 的点分布在不同参数位置，提示 SPT 曲线参数补偿；不证明唯一材料参数。D10 有已接受尝试中的大应变警告；D07 有极小末帧反力回落，保守不评分。全部原始来源、逐项评分与图表保存在 Git 忽略的[私有报告](artifacts/private/main/REPORT.md)及[逐项表](artifacts/private/main/review_table.csv)。

目前建议先离线澄清 D09 终态及 D10/D07 数值证据，再讨论新的受限 BO/DE FE 授权。既有 run_025 BLOCKED 与盲测历史暴露结论不变；未执行任何新增求解、入队、重试、优化或解盲。
