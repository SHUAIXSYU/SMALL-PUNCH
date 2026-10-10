# run_002 双语内容与科学表述审阅

审阅对象：README.md 与 README.zh-CN.md。两个版本按相同 16 节编写并逐节核对；本审阅为人工语义检查，不能由关键词检查替代。

| 范围 | 对齐结论 |
| --- | --- |
| 1–3 项目、物理问题与目标 | 研究名 SP-InvOpt，仓库名 SMALL-PUNCH；SPT 是拟研究系统，不冒充实际几何已知；横梁位移、压头位移和系统柔度明确区分。目标均无已取得性能提升声明。 |
| 4 架构 | 相同五层、九节点和十条连线，按补充要求两种语言均使用相同英文图标注。优化回路与独立物理验证分开；最终节点是目标产出。所有计算功能为规划，AbqJobPilot 未集成。 |
| 5 本构 | 候选 Hollomon 与分段连续形式一致；K 受连续性约定约束；E 初期固定但未给数值。工程/真实、总/塑性/等效塑性严格区分，未解决定义及偏移差异保留为 Open Questions。 |
| 6 反演 | 同一带物理允许域和权重的最小二乘表达式；统一位移坐标，处理噪声、柔度、接触和几何不确定性。拟合好不等于唯一或物理正确。 |
| 7 RL 角色 | 均为预算约束序贯参数选择；三种传统优化为必要基线；PPO/SAC 仅候选。两参数单次任务可能传统方法更高效，不承诺优于 BO。另增相同英文 Mermaid 闭环，8 节点/9 连线，训练更新为虚线，部署可固定策略。 |
| 8 MDP | 八个全文展示公式逐字对应，包括状态、动作和奖励。两版本均说明变长数据编码、任务上下文、Markov 信息充分性、初始有效解、归一化动作、成本单位、预算扣除、失败与终止规则，以及训练/部署分开计费。 |
| 9–10 研究问题与路线图 | RQ1–RQ3、评价指标、四阶段任务和状态等价。Stage 1 尚未完成 CAE sanity；Stage 2–4 为 Planned。 |
| 11–12 结构与环境 | 基于实际公开文件树；CAE/Jobs 单独标为尚不存在的规划目录。环境依据 run_001，版本查询与真正求解能力分开；不发布本机安装路径或伪造安装流程。 |
| 13–14 状态与数据 | 均保留 run_001 WARNING、五文件哈希核验和八包导入、17 项轻量检查的历史范围。run_002 无提交/推送；隐私边界、导入来源和当前科学结果无法独立复现的限制一致。 |
| 15–16 局限与引用 | 相同七项限制；没有杜撰论文、作者、DOI 或 BibTeX；联系仅指向已提供仓库入口。 |

## Mermaid 与数学可读性

图采用 TB 布局、五个带编号层、简短引号标签、统一 ASCII 节点标识。主路径从数据经控制器/参数/运行器/FE/提取进入目标评估，只有一条优化反馈回路，另有候选解到独立验证路径。逐条核对端点及双语对应，没有引用 undefined 节点。最终节点文字较长但未混入公式、嵌套图或复杂样式。

Python 检查覆盖本图所用的有限 Mermaid 语法、子图平衡和拓扑；没有本机 Mermaid/KaTeX 模块，未安装依赖。**没有通过真实 Mermaid/MathJax 渲染或 GitHub 页面预览验证布局。** 不能将语法检查报告为渲染通过。公式采用 GitHub 支持的美元定界符、标准 LaTeX 命令和 cases 环境。

## 原创 SVG 物理与视觉核验

`docs/figures/spt_setup.svg` 表现轴对称截面的初始接触状态：薄圆片位于上夹持面和下支承面之间，下模中央开口、圆角支承边缘和压头通道分明，球形压头在中心接触圆片。向下 u 箭头表示施加位移，轴向传感器附近向上 F 箭头表示压头所受反力。图内和两份 README 图注均声明示意、不按比例、实际尺寸与传感器布置未核验；没有网格、实验数据或材料参数。

使用现成 sharp 渲染为 1120×650 PNG 后实际查看，所有标签与引线清晰，无裁切或重叠。白底、深色英文标签、蓝色位移箭头及棕黄色薄片使物理部件容易区分。白底由 SVG 内部矩形提供，GitHub 明暗主题均不会使文字与背景混色。SVG XML 另检查无 script、外链、事件处理器、远程字体或嵌入光栅图。PNG 仅是审阅预览，不进入 README；主页直接使用同一 SVG。

## 证据边界与公开链接

- 本次未打开 references_private 中的文件，也未读取 run_001 的私有源数据审计内容。只使用现有公开文档中的已登记结论。
- 只读查看 AbqJobPilot 的公开主页确认所给链接；没有代码/API 审计或集成测试，没有修改外部项目，不沿用其性能宣传数字。
- 本次参考 [GitHub diagrams](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams)、[GitHub mathematics](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/writing-mathematical-expressions)、[Mermaid flowchart syntax](https://mermaid.js.org/syntax/flowchart.html) 和 [Abaqus 文档镜像](https://abaqus.uclouvain.be/English/SIMACAEGSARefMap/simagsa-c-matdefining.htm)，访问日期 2026-10-10。未把外部文档内容当作本项目已实现功能。
- 原始数据、材料数值、文件名、图片、安装绝对路径均未加入双语主页。
