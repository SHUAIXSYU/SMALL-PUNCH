# run_005 — Existing ODB / JNL 只读审计

状态：**WARNING**。已实际读取 Abaqus ODB、提取真实 Punch RP 曲线、审计 Journal/INP/日志并形成分层准入结论。仅 ODB 提取链路 PASS，不能据此宣称模型物理验证全部通过。

## 本轮结果

- 找到 Sanity 和 TempTry 两组同名 Job 文件，各有 ODB/INP/STA/MSG/DAT/LOG、CAE、JNL 及伴随文件，共24个文件登记相对路径、大小、时区明确的文件修改时间、SHA-256、角色和来源。完整清单在忽略的 [私有审计区](artifacts/private/file_inventory.json)，[公开索引](artifacts/file_inventory.json)保留入口。
- 用 Abaqus 2024 自带 Python 3.10.5 及 odbAccess，以 readOnly=True 成功打开 Sanity Job-1.odb。ODB、STA、DAT、LOG 一致支持 Job 正常结束；这不是整体物理正确性证明。
- 通过 INP 刚体定义、集合成员及 ODB History Region 确认 Punch RP 为 `ASM_SPT.1`。U2/RF2 均来自该 RP，共181个同步点、181帧。History 与 Field 位移/反力逐点一致。
- 原始末点 U2≈−0.001200000057、RF2≈−755.8928833。正向压入采用 d=−U2、F=−RF2，无绝对值、插值或额外2π。单位声明未确认，CSV/图使用模型单位；若后续确认 m–N–Pa，则约为1.2 mm、755.893 N。
- 完成 U2–time、RF2–time、F–D、能量及真实输入网格图。原始数据没有平滑、修补或伪造。曲线单调但存在局部陡增，特别是增量160附近。
- Journal 提供轴对称试样/Punch、E=2.1e11、ν=0.3、1251行塑性表、外环夹持、硬接触/μ=0.1、Static/NLGEOM、CAX4与输出配置证据。按操作顺序确认初始自由转动后来改为DOF6=0；当前 INP 与 ODB 支持最终旋转已受约束。
- 数值警告未掩盖：45次失败尝试、MSG 51个警告头；4次负特征值和4次畸变警告均位于被拒绝的尝试，随后 cutback 并收敛。材料应变语义、轴线径向约束、网格/增量敏感性和完整接触能量仍待验证。
- 两组 INP 哈希相同、ODB 哈希/创建时间不同；分别提取后，U2/RF2及8项能量历史逐点一致。这提供有限历史重复证据，不等于本轮受控重算或 CAE→INP 可复现已通过。

## 准入结论

| 层级 | 结果 |
| --- | --- |
| Level 1 — Model Evidence | WARNING：有可追踪求解设置，物理输入语义等仍未决 |
| Level 2 — ODB Extraction | PASS：同一真实 RP 的模型单位 F–D 提取与变换已验证 |
| Level 3 — Forward Reproducibility | WARNING：两个历史同输入结果一致，完整受控复现未验证 |

**现阶段不批准直接进入正式参数化求解/反演。** 后续先确认材料、单位和轴线/边界需求，再另行授权模型修订及受控 Solver/敏感性验证。没有实验曲线，不报告实验拟合误差。

## 交付

- [ODB 审计](artifacts/odb_audit.md)
- [Journal / INP 审计](artifacts/jnl_model_audit.md)
- [分层准入判断](artifacts/forward_model_readiness.md)
- [后续建议](artifacts/stage2_recommendations.md)
- [原始 RP CSV](artifacts/punch_rp_history_raw.csv)、[正向 F–D CSV](artifacts/punch_force_displacement.csv)
- [F–D 图](artifacts/force_displacement.png)、[U2–time](artifacts/punch_u2_time.png)、[RF2–time](artifacts/punch_rf2_time.png)、[能量图](artifacts/energy_diagnostics.png)
- [数值统计](artifacts/numerical_sanity.json)、[提取规则](artifacts/extraction_metadata.json)
- [Abaqus 只读提取脚本](artifacts/extract_odb_readonly.py)、[普通 Python 分析脚本](artifacts/analyze_extraction.py)、[Journal/INP 文本审计脚本](artifacts/audit_text_sources.py)

所有新报告、脚本、数据与图均位于本 Run。仅另更新 Run 索引和项目状态；未修改旧 Run、AGENTS、忽略规则或原始模型。

## 执行与验证边界

遵循 AGENTS 和 Run 协议，先读取项目状态、最新 run_004、.gitignore，独占创建 run_005。Git 初始为 main / `a52be779f3b6ae9f830573764d5eed439df70b3b`，origin 为 SMALL-PUNCH 仓库。已有 run_004 未跟踪记录、两处状态文档未提交改动和两个 CAE 目录均保留。初始证据及修改前状态文档快照位于 checkpoints/；未重置旧改动。

首次时钟观测为2026-10-12T18:31:41.656183+08:00，早于该观测的读取开始时间未知。科学分析使用用户指定 Torch-GPU Python；Abaqus API 使用其自带 Python，不跨环境导入 odbAccess。既有 pytest/iniconfig 依赖缺失未修复；本任务直接执行独立脚本，不调用 pytest。未安装依赖或修改共享环境。

首次 ODB 提取因 float32 的 JSON 序列化失败；保留失败脚本/控制台。修复后成功，随后因需要 UR3/RM3 和哨兵值诊断做了有明确目的的第三次只读提取。PowerShell JNL 哈希查询曾遇共享占用，未强制处理；后续只读校验一致。所有错误、外部文档403与最终验证范围见 run.json/checkpoints。

已执行验证包括原始文件 SHA-256 保持、历史 Run 保持、Git HEAD/branch/index 保持、INP/ODB拓扑对照、同节点 History/Field 对照、CSV回读、符号与行数、实际生成图像目视检查及静态产物哈希。最终结果见 [验证记录](checkpoints/final_state.json)。未把失败检查写为零误差。

未运行 Solver、datacheck、Job submission、Journal replay、训练或优化；未打开/修改 CAE，未生成 INP，未 commit/push，未调用 AbqJobPilot。下一步新的求解需要用户明确授权。本轮完成后停止，不自动进入 run_006。
