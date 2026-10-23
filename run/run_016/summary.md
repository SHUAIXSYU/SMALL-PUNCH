# run_016 — Experimental-to-FE Qualification

**BLOCKED（正式反演准入）；离线审计已完成。** 新增 Solver/Datacheck、Queue 写入、FE 搜索、RL、自动重试和 Git commit/push 均为 0。

## 实际完成

- 合作方条件作为新的私有声明登记，保留 run_015 原结论。
- MAIN 经 AgentHub 分配真实 CAE 与 ODB 会话；两任务完成，14 项产物哈希及完成消息核验通过，并留存 MAIN 确认。
- CAE 核对实际候选 INP 身份和名义试样尺寸；固定环带缺少已验证的下夹具接触等效性，实际冲头/夹持仍待确认。
- ODB 核对 SPT 两容器相同数值序列、标签冲突与预先登记的峰前窗口规则。单位冲突未解决；窗口保持 PROVISIONAL。
- MAIN 复现冻结的探索性 Loss，解释归一化含义；原 12 项加 7 项资格测试，共 19 项合成测试通过。Loss 实现及旧配置未改。
- 基于公开资料和明确工程假设，定版探索域及分阶段预算规范；这是离线协议，新 Job 授权仍为 0。

## 准入结论

CAE 几何 **BLOCKED**；SPT 单位 **UNRESOLVED**；位移定义 **WARNING**；Loss/窗口 **PROVISIONAL**。当前不具备申请 DE/BO 新 Job 的条件。未来解决资格问题后，可先申请最多 5 个先导计算（中心及两参数各正负方向），而不是自动消耗 48 个规划上限。

## 证据与修改

- [私有总审报告](artifacts/private/main_qualification_report.md)
- [CAE 私有报告](artifacts/private/cae/geometry_qualification.md)
- [ODB 私有报告](artifacts/private/odb/spt_qualification_report.md)
- [参数与预算协议](artifacts/parameter_and_budget_protocol.md)
- [定版协议身份](artifacts/inversion_qualification_contract.json)
- [Loss 测试](artifacts/loss_test_results.json)
- [AgentHub 登记](artifacts/agenthub_receipt.json)
- [证据清单](artifacts/manifest.json)

新文件仅在本 Run；更新 Run 索引及项目状态。8 个明确基线文件（SPT 源、候选输入、既有 FE CSV、Loss/配置、Abq Queue/project.db）哈希保持；原始实验/模型未编辑，外部项目未修改。所有可恢复实验数据位于 Git 忽略的私有区域。

## 隔离与停止

研究为“独立数据保留验证，存在历史信息暴露”。run_015 的 MAIN/ODB 暴露记录保留；本轮没有继续访问保留拉伸源及派生内容。严格独立审查需未接触者或隔离流程。

后续应先取得最小缺失条件、资格审查/必要模型变更授权，再冻结正式目标。BO 实现及合成验收尚待完成。建议不构成计算授权；本 Run 完成后停止。
