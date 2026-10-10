# Stage 1 / run_002 — Research README & GitHub Documentation

状态：**WARNING**。中英文研究主页已完成；由于 run_001 尚未提交且共享文件改动混合，本次按用户规则未自动 commit。没有 push。真实 GitHub Mermaid/MathJax 渲染未执行，采用轻量静态检查和人工语义审阅。未宣告无条件 PASS。

## 本次任务与实际执行

为研究项目 SP-InvOpt（Small Punch Inverse Optimisation）建立专业 GitHub 研究主页，仓库名称仍为 SMALL-PUNCH。首先读取 AGENTS、现有 README、研究概述/架构/本构/通信/数据管理文档、项目状态、Run 索引和 run_001 记录；检查 Git 分支、HEAD、remote、working tree、.gitignore 与公开目录树。

随后保存四个共享文档的精确修改前快照，记录公开文件基线哈希，再编写默认英文 README 和对应中文版。没有打开 references_private 的文件或读取其中敏感内容，也没有读取 run_001 私有内容审计。本次仅引用已有公开审计摘要，不重新核验或发布原始数据。

首次工具时间观测为 2026-10-10T18:08:08+08:00，作为 Run 记录起点；实际结束时间见 run.json。没有编造更早的精确起始时间。

## 内容交付

两份 README 具有相同 16 节：项目概述、SPT 物理问题、目标、五层架构、本构模型、反演表达式、RL 角色、MDP、三个研究问题、四阶段路线图、真实目录树、环境、当前状态、可复现性/数据、研究边界与引用联系。

- 五层 Mermaid 图明确全部计算环节为规划，产出为研究目标而非已有结果；Agentic CAE 与 Abaqus 求解器职责分开。
- Hollomon、分段连续式与初始参数向量保持现有契约，不添加数值，保留应变测度及偏移差异为 Open Questions。
- RL 表述为计算预算约束下的序贯参数选择。MDP 说明变长历史编码、归一化动作、奖励成本尺度、初始化、失败求解、预算及终止规则，并区分训练成本与部署 FE 成本。
- RQ1 计算效率、RQ2 参数可识别性、RQ3 泛化迁移明确评价指标。Stage 1 模型 sanity 仍受阻，Stage 2–4 为 Planned。
- 保留 run_001 WARNING、5 文件完整性、8 包可用、17 项轻量检查及 Abaqus 查询的真实范围。不把文档、文件或环境审计说成 CAE/物理验证。
- 未编造论文、DOI、作者或引用格式。AbqJobPilot 仅为潜在外部执行层，公开主页只读核对不等于接口已核验。

## 科研可视化补充交付

按用户在执行期间追加的要求创建 `docs/figures/`，包含原创 `spt_setup.svg` 及用途/维护说明 README.md。SVG 为初始接触状态的轴对称截面，表现薄圆片、球形压头、上夹持模具、下支承模具、中央向下位移和轴向载荷传感器测力。图注说明反力方向与位移方向，以及实际几何/传感器布置未核验；不按比例、不包含网格或实验数据。

两份主页在 SPT 章节共同引用 `docs/figures/spt_setup.svg`。五层 Agentic CAE Mermaid 图保留，另增 RL–Abaqus–Reward–Policy Update 闭环图，训练策略更新采用虚线，推理部署可以固定策略。全部图使用英文标注，两份 README 的 Mermaid 源码完全一致。SVG 为白底深色文字、纯矢量、无脚本/外部字体/远程资源。

使用已存在的 sharp 成功渲染并查看 `artifacts/spt_setup_preview.png`，确认文字和引线无重叠/裁切、圆片夹持与中央开口关系明确。预览仅作审阅证据，README 使用 SVG。没有获取论文图片或生成实验曲线。

## 修改文件与归属

| 路径 | 来源与本次变化 |
| --- | --- |
| README.md | run_001 遗留修改文件；本次经明确授权改写为英文主页，旧内容精确快照保留。 |
| README.zh-CN.md | run_002 新建；与英文实质一致。 |
| docs/Research_Overview.md | run_001 未跟踪文件；仅更新 SP-InvOpt 研究命名及 run_002 文档阶段说明。 |
| run/README.md | run_001 未跟踪文件；保留原索引，追加 run_002。 |
| status/PROJECT_STATUS.md | run_001 未跟踪文件；保留已有事实，更新当前 Run、文档交付与提交/验证限制。 |
| run/run_002/ | 本次新建元数据、总结、产物清单、文档检查脚本/结果、语义审阅及检查点。 |
| docs/figures/spt_setup.svg、docs/figures/README.md | 补充可视化任务新建的原创 SPT 示意与用途说明。 |

其余 run_001 文件和 .gitignore 不改动。`checkpoints/initial_state.json` 保存初始 Git 状态及全部非私有既有文件哈希；`checkpoints/before/` 保留四个共享文件的 `.snapshot` 字节副本。旧文件不会因本次改写而丢失，可据此逐段审阅差异。

run_001 的 manifest 和检查脚本具有历史基线含义，其中 README 前缀检查针对旧主页。此次没有改写历史记录，也未重新运行会读取私有区的旧检查；使用新的文档检查脚本核验当前交付。共享文档的历史哈希改变是本次有记录的授权变更，不冒称旧哈希仍描述当前主页。

## 验证

执行方式：使用 run.json 指定的现成研究 Python 运行 `run/run_002/artifacts/validate_readme.py`，不安装新依赖。补充图示后的 **20 项轻量检查全部通过**，精确检查状态见 `artifacts/validation.json`。SVG 渲染和目视检查另见 `artifacts/svg_render.json`。

检查涵盖文件/UTF-8、顶部语言链接、16 节对应关系、标题层级、代码/数学围栏、8 个公式逐字一致、LaTeX 花括号、两张有限 Mermaid 语法及双语英文源一致、相对链接、图片路径、SVG 自包含/英文标签/背景、绝对路径/私有证据泄露筛查、状态标记、四阶段状态一致、明显不实完成声明筛查、既有工作与快照、Git HEAD/暂存区和私有目录忽略规则。

首次检查把 HTTPS 中的 `s:/` 误报为磁盘路径，且 Windows 管道默认编码导致中文报告乱码。已加路径词边界并改用 ASCII JSON 转义输出；失败尝试保存在 checkpoints/validation_attempt_01.json，最终报告为修复后真实执行结果。补充图示之前的 17 项已通过，最终报告增加 SVG 和图片检查。

`artifacts/Editorial_Review.md` 记录人工逐节语义、科学边界和图示可读性审阅。程序中的声明筛查是辅助规则，不冒称能证明所有自然语言结论正确。Mermaid/KaTeX 模块不可用，未安装；静态语法检查不等于真实渲染通过。没有发布至 GitHub 来获取预览。

## Git 状态与 commit 结果

初始分支 `main`，HEAD 为 `f8fbdbe8d3ccd484eb5b23567084c45c66baab62`，origin 指向用户给定 GitHub 仓库。README 已修改，其他 run_001 基础文件未跟踪，暂存区为空。精确最终状态见 `checkpoints/final_state.json`。

**本次 commit：未执行。push：未执行。** run_001 与本次共享文件改动混合，若只提交新版 README，会丢失清晰的基础阶段归属并引用尚未提交的文档。按用户规则保留工作区，不自动暂存或提交；未执行 reset、clean 或覆盖其他改动。

建议提交范围（须先审阅并处理 run_001 基线，当前不执行）：README.md、README.zh-CN.md、docs/Research_Overview.md、docs/figures/、run/README.md、status/PROJECT_STATUS.md，以及 run/run_002 的非私有文档、记录、检查脚本和检查点。四个共享文件应相对保存的 run_001 快照审阅本次增量；本次不要把其他 run_001 文件或私有资料混入文档提交。仅有本次新增文件也不宜单独提交成依赖不完整的主页。

## 未解决事项与下一步

文档之外仍缺可审计 CAE 模型、已确认实验曲线及本构定义。AbqJobPilot 未集成，优化器、代理模型和 RL 未实现。本次没有重新检查许可证或运行能力。

下次明确授权后，可先整理阶段提交边界和 GitHub 实际渲染，再按科研优先级补齐模型/实验来源并澄清本构应变定义。本任务结束后停止，不进入 run_003。
