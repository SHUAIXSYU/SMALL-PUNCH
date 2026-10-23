# run_015 — SPT 离线审计与盲反演协议

状态：**WARNING（本轮离线工作完成；正式反演未准入）**。

## 实际完成

- 真实ODB会话完成两份SPT资料的逐点核对，MAIN选定可追溯的候选数值基准；转换、原值、图与残差全部位于Git忽略区。
- 真实CAE会话核对既有INP/JNL的试样、压头、约束及加载定义；模型设定与实际实验条件的对应仍待确认。
- 独立Loss函数和12项合成单元测试通过。冻结原始采样窗口、权重、力尺度，已有FE探索性对照标为PROVISIONAL，未作正式实验拟合结论。
- 冻结探索性边界、初始设计和48个唯一新Job预算；当前获准/实际新增FE均为0。边界是一般数值假设，不是已验证材料范围。

## 用户策略变更与信息泄漏

用户在本Run中先追加拉伸资料审计，之后明确禁止继续访问并将其留作解盲验证。新禁令前，MAIN和真实ODB会话已读取并分析该资料；**已经暴露，不能称完全盲测**。禁令后停止访问及使用，已有产物原地封存，不删除或改写。CAE访问该资料没有在当前证据中出现，未进行主机级无访问证明。

当前入口仅为[盲反演协议](../../docs/Blind_Inversion_Protocol.md)、[冻结契约](artifacts/blind_inversion_contract.json)和[SPT私有报告](artifacts/private/spt_final_report.md)。旧混合审计和拉伸派生产物禁止继续读取；路径见私有访问策略。原SPT数据/配置未变，不利用保留资料调整边界、初值、Loss或预算。由于此前接触不可撤销，正式计算前需未接触保留内容的审核者复核。

## 验证与交付

- [Loss测试](artifacts/loss_test_results.json)：12/12通过，全部合成数据，无Solver。
- [协议检查](artifacts/protocol_checks.json)：冻结SPT哈希一致，预算求和与零授权检查通过，18项SPT/CAE角色证据哈希通过。
- [当前结果](artifacts/offline_result.json)、[真实会话交付](artifacts/session_delivery.json)、[停止确认](artifacts/holdout_stop_acknowledgements.json)。最终MAIN登记回执见artifacts/agenthub_final_receipt.json。
- [最小SPT问题清单](artifacts/private/spt_minimum_questions.md)。正式实验单位/测点/零点/柔度/条件、FE数值充分性尚未通过。
- 源和Queue/Project DB完整性核验仅覆盖当前允许的SPT/既有FE/模型文本；封存资料不为再核验哈希而重新读取。

## 修改文件与限制

新增inverse/fd_loss.py、本Run代码/元数据/私有证据及docs/Blind_Inversion_Protocol.md；AGENTS.md持久记录用户禁读规则，.gitignore补充封存元数据规则；更新Run索引与项目状态。保留用户预先存在的Project DB改动。

没有新增Solver/datacheck、入队、INP、DE/BO/RL、依赖安装或commit/push。run_014单次授权已经用完。后续真实反演须另立Run及新授权；最佳参数、不确定性、Loss、调用数和全部证据冻结后仍须用户明确解盲。本轮完成后停止。
