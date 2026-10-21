# 研究架构

## 进程与目录职责

```text
实验数据导入/预处理（experiments/，来源可追溯）
        ↓
外部 Python Controller（inverse/，未来实现）
        ↓ JSON 参数、作业请求
Abaqus Job Interface（CAE/Scripts/，未来实现）
        ↓
Abaqus Python / CAE / Solver（CAE/Jobs/<run_id>/<job_id>/）
        ↓ ODB 只读提取进程
结构化结果 JSON + CSV → 曲线比较 → Controller
        ↓
run/run_XXX/ 元数据、相对路径、校验、诊断、总结
```

模型源及生成模型统一放 `CAE/Models/`，区分 source 与 generated 子目录时登记来源。私有资料中的原模型仍保留不动；未来经批准导入的工作副本才进入 CAE。`CAE/Jobs/` 为未来独立作业工作目录且整目录忽略；run_008 在 `run/run_008/artifacts/candidate_inp/<unique_job>/` 生成了一个候选 INP，但没有创建 Queue item、datacheck 或 Solver Job。`run/` 不充当大型模型仓库。

外部 Python 负责科学计算与调度；Abaqus Python 负责产品 API、建模和 ODB 读取。两者不共享 Python 模块依赖。命令使用显式解释器和受控 cwd，记录返回码、标准输出/错误、版本、超时及文件存在性。环境变量只白名单传递，不输出凭证。版本查询成功不代表许可证、CAE 或 Solver 已可用。

参数对象未来包含 name、value、unit、role（fixed/inferred）、bounds、source_ref 与 schema_version。当前 `sigma_y`、`n` 为 inferred，`E` 为 fixed；正式数值、边界、泊松比和单位系统待核验。改变 E 的角色时也须重新计算依赖 E 的材料转换，不能沿用旧材料表。

## Agentic CAE Runtime / AbqJobPilot 接口

run_008 复用了本机 `D:\Projects\abqjobpilot` 稳定版 v0.2.2。五个只读/预览 MCP 工具和公开 Python API 已实际核验。Project 身份、Queue/History 列表、状态和输出定位已调用；Queue 保持空且哈希不变。由于全局及独立 Project Settings 缺失，未调用 preflight 和 dry-run enqueue；没有用代码默认资源设置替代。稳定版能力存在不代表每项能力都已在本机可执行。

| 接口 | 计划输入 | 计划输出 | 当前核验 |
| --- | --- | --- | --- |
| capabilities / Project | AbqJobPilot 公共 API | 稳定版能力与 formal Project 身份 | v0.2.2 / Project API 已核验 |
| preflight / dry-run enqueue | INP、Job 名、资源设置 | 输入预览、命令预览、无 Queue 写入 | API 存在；本轮因 Settings UNKNOWN 未调用 |
| Queue / History / status | Project、queue/job ID | 已登记状态与历史摘要 | MCP Queue/History 空列表及候选 UNKNOWN 已调用 |
| locate_outputs | 唯一 Job 或 INP | 预期 ODB/STA/MSG/DAT/LOG/LCK 路径 | MCP 已调用；候选输出不存在 |
| extract_results | ODB、step/region/component 契约 | 曲线 CSV、JSON 元数据及质量标记 | 既有 run_005 提取已验证；run_008 只验证只读 U2/RF2 接口 |
| failure_diagnostics / retry | 状态、日志、缺失输出 | 错误分类及受控恢复 | Project 生命周期仍由 AbqJobPilot 管理；未授权 retry |

集成证据和限制见 [run_008](../run/run_008/summary.md)。重试必须记录新 attempt，不覆盖旧日志；不能无限自动重试。失败不得返回伪造曲线或零损失。Hub 的 task/approval 不替代 AbqJobPilot Queue/Runner 控制。

## 结果契约（规划）

作业请求包含 schema_version、run_id、job_id、attempt、模型路径/哈希、参数及单位、分析配置、输出提取配置和时间限制。结构化响应包含 status、outputs、validation、errors 和实际执行版本。

曲线 CSV 候选列为 time、displacement、force；JSON 必须说明每列单位、位移零点、正负号、采样方法、step、region、分量、聚合及对称缩放方法。RF/U 只是待核验的提取候选，不能在当前假定某节点、RP、U2/RF2 或倍率正确。实验位移可能来自横梁或冲头，须确认设备柔度及测量定义。

曲线比较需先批准共同位移区间、对齐、插值、加载/卸载分支、权重、异常点和目标函数。当前仅定义所需契约，不实现比较或优化。
