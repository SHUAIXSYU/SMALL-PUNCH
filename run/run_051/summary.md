# run_051 — 高应变硬化包络离线准备

**WARNING / READY_TO_REQUEST_TWO_EXPLORATORY_SOLVES。**

已核实run050两种塑性功口径，并以冻结D01为唯一基准完成H01/H02后续硬化扰动。幅度和过渡在材料表/新INP生成前冻结；保留低段与原数值控制，未反向拟合任何拉伸资料。

18项离线单元测试通过，材料表插值界和实际切线检查通过；真实CAE通过AgentHub完成两份独立INP，MAIN独立核对只有塑性表行变化，公开API2/2 Preflight与2/2 Dry-run通过。Queue/Settings未变，未执行Solver、Datacheck、入队或优化。

完整[私有报告](artifacts/private/REPORT.md)、[材料契约](artifacts/material_contract.json)、[未来比较协议](artifacts/comparison_contract.json)、[冻结候选清单](artifacts/prepared_batch.json)和[材料对比图](artifacts/private/material_envelope_comparison.png)。工程包络不是真实材料置信边界，准备/预览不代表科学验证。可申请两次新的独立求解，当前未授权执行；停止等待用户决定。历史冻结预测、NOT_EVALUABLE及暴露声明保留。
