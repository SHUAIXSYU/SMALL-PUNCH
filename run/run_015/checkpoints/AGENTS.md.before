# SMALL-PUNCH Agent 工作契约

本仓库研究小冲杆试验（SPT）弹塑性本构参数反演。项目名保持 SMALL-PUNCH。

## 执行边界

- 先读 `status/PROJECT_STATUS.md`、`run/README.md` 和最近 Run 的 `run.json`、`summary.md`。
- 每项独立研究产出登记新的 `run_XXX`。编号递增且不复用，完成后等待指令，不自动进入下一 Run。
- 开始前记录 Git branch、HEAD、remote、working tree。保留用户改动，不覆盖、删除既有资料；不擅自 commit、push 或修改外部项目。
- 所有工作输出留在本仓库。外部解释器和 Abaqus 仅作为只读调用的工具，不改动其安装或环境。
- `references_private/` 是不可修改原始资料区。禁止写入、清洗、重算、另存覆盖或以其为 CAE 工作目录。保留 `/materials/` 和实际历史拼写 `/Materials/` 忽略规则。
- 导入资料时记录源文件相对路径、SHA-256、许可/来源、处理方法及版本；输出进入 `experiments/` 或 `CAE/Models/`。源路径、原始数值和来源明细默认留在忽略的私有审计区。
- 目录迁移遇到冲突、已跟踪文件、占用或校验失败必须停止，不强制覆盖。

## 环境与运行

- 优先使用用户指定 torch-gpu 解释器。具体路径见 `run/run_001/run.json`。不可用时标记 BLOCKED，不自动换环境或安装依赖。
- 外部科学计算 Python 与 Abaqus Python 分进程；通过 JSON/CSV 文件交接，不假设 Abaqus 能导入 SciPy、PyTorch 等包。
- Stage 1/run_001 只做只读审计与轻量验证；不得求解、训练、优化或生成正式材料表。
- 后续求解须有明确任务授权、可审计输入与单独工作目录。大型 ODB、SIM、LCK 和中间文件不得入 Git。
- AbqJobPilot 接口目前全部为规划，未核验任何实现。不得修改该外部项目。

## 科研证据与交付

- 事实、推断、规划分别记录；无法验证写 UNKNOWN，不能按文件名猜模型设置。
- 不混淆 engineering/true stress、total/plastic/equivalent plastic strain。公式差异先登记，不能静默统一。
- 时间用真实观测值及 ISO 8601 时区，无法确定用 null 并说明。失败需保留错误信息；不能把失败当成零误差。
- Run 至少有 run.json、summary.md、artifacts/、checkpoints/。artifacts 优先记录相对路径和校验值，不复制大型模型或结果。
- 更新 Run 索引和项目状态。PASS 只说明明确列出的检查范围；关键条件未满足时用 WARNING 或 BLOCKED。
- 不提供未执行的测试结果，不伪造实验曲线。完成当前指令即停止。
