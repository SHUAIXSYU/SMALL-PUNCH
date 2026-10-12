# Journal / INP 模型审计

状态：**WARNING**。Journal 仅作文本解析，未执行、replay 或导入 Abaqus。对 JNL 使用 AST 解析和数值字面量读取；完整操作顺序及 Plastic table 见 [private/journal_operations.json](private/journal_operations.json)。与本次求解关联的 INP 为主证据，完整逐块记录见 [private/inp_blocks.json](private/inp_blocks.json)。未打开 CAE，不能确认当前内存模型或已保存 CAE 与 INP 完全相同。

## 关联关系与时间边界

Sanity 中存在用户指定的 CAE 和同名 JNL；JNL 最后保存注释为 `2026_10_12-17.52.07`，与文件 mtime 相符。JNL 内包含两次 Job-1 submit 及完成消息，时间字符串为 `Mon Oct 12 00:49:33 2026`、`Mon Oct 12 00:57:06 2026`，字符串未写时区，因此保留原文，不自动赋予绝对时间。

TempTry 的 atry.jnl 与 Sanity JNL 的 2783 行文本逐行比较，只有最后的 Save 时间注释不同，其余建模和 Job 消息相同。TempTry LOG 的旧计算时间与 JNL 消息相符；Sanity 现有 Job 的 ODB 创建时间为 18:17:12+08:00，晚于 CAE/JNL 的保存时间。因此 Sanity JNL 含继承的早期操作/求解历史，不能当成 18:17 本次提交的完整操作日志。两目录 INP 的 SHA-256 完全相同，支持最终输入设置一致；不证明 CAE 文件内部状态一致，也不证明中间没有修改。

## Geometry、装配及 Reference Point

| 证据 | 识别内容与边界 |
| --- | --- |
| JNL 22–27 | specimen 矩形 `(0,0)` 到 `(0.005,0.0005)`；AXISYMMETRIC / DEFORMABLE_BODY |
| JNL 29–56 | 划分试样区域；草图有一次 undo，不能沿用被撤销的矩形尺寸 |
| JNL 57–175 | Punch 多次草图重建、裁剪，早期草图删除；最终圆心 `(0,0.00125)`、半径 0.00125 的圆弧 |
| JNL 176–180 | Punch 为 AXISYMMETRIC / ANALYTIC_RIGID_SURFACE，AnalyticRigidSurf2DPlanar |
| JNL 705–711 | Punch 实例 ASM_SPT，specimen 实例 ASM_SPT-1；Punch 平移 `(0,0.0005,0)` |
| JNL 724–729 | 最初在 `(0.002,0,0)` 创建 RP，随后删除该 RP，重建于 Punch vertex；不能把最初位置当作最终值 |
| INP 1374–1383 | 实例局部 node 1 坐标约 `(0,0,0)`，与 Punch RP 两集合一致；解析面 START `(0.00125,0.00125)`，CIRCL 至 `(0,0)`、圆心 `(0,0.00125)`；Rigid Body 明确引用该 RP 与面 |
| INP / ODB | 试样节点范围 r=0–约0.005，z=0–约0.0005；Punch 最低点经装配位移后在 z≈0.0005 |

数值均为模型长度单位；m/mm 的物理解释尚未正式确认。最终几何由 INP 节点/连接和解析段确认，未靠面名猜尺寸。名义初始接触在试样顶面轴线处；浮点节点写出误差不等于有意设置间隙。

## Material and Section

- JNL 182 起创建 `MAT_SPECIMEN_INV`；686–687 改名 `Q200N01`，当前 INP 名称同为 Q200N01。
- Elastic：E=`2.1e11`、ν=`0.3`。若采用 m–N–Pa，则 E=210 GPa；该单位说明是条件解释。
- Plastic：1251 行。首行 `(2e8,0)`；末行 INP 约 `(5.53968e8,24.999)`。JNL 全精度表及 INP 写出值分别保存，没有修改、重算或生成新的正式材料表。
- 数字格式检查：首点塑性应变为零；应变列严格递增，应力列非递减；但最大应变约 25，是否存在百分数/小数或应变测度问题 **UNKNOWN**，不能以求解成功认定数据正确。
- 第二行应变 `0.019047619` 等数值与“总应变序列减固定 `sigma_y/E`”的模式相容，这是与既有 CM-002 问题相关的**推断**，不是已证实来源。Journal 本身没有应力/应变测度、单轴试验来源、转换公式或单位说明。
- 常规金属塑性要求真实应力及相应塑性应变；从总应变转换时应扣当前应力对应的弹性应变，不能仅因为第一行是零就认为整表语义正确。[Abaqus 原厂手册：Defining plasticity](https://abaqus.uclouvain.be/English/SIMACAEGSARefMap/simagsa-c-matdefining.htm)。因此该表只通过数字结构检查，物理定义 **NOT VERIFIED**，既有 [本构契约](../../../docs/Constitutive_Model.md) 的未决项未解除。
- JNL 697–702：HomogeneousSolidSection `Section-1`，材料 Q200N01，赋给 `set_specimen_all`；INP `*Solid Section` 赋给全部 594 个单元。
- 未发现 Density、损伤演化、材料应变率或温度依赖定义。本次静力输入未因缺失密度而被判断为无效；但不能据此用于动力学或断裂预测。

## Boundary Conditions 与 Step

JNL 712–714 与 INP 2677–2679 一致：Static、NLGEOM=YES、Step_Punch_Displacement；初始增量 0.01、Step 时间 1、最小增量 1e-12、最大增量 0.1、最大增量数 999999。未设置稳定化系数，ODB ALLSD=0；未据此认定不存在任何接触算法耗散。

Punch BC 的执行顺序尤为关键：JNL 757–761 首次定义 U1=0、U2=−0.0012、UR3=UNSET；第一次旧 Job 完成后，1124–1125 将 UR3 改为 0，再提交第二次旧 Job。当前 INP 的最终 BC 明确包含 DOF6=0。ODB Field 存在 UR3/RM3，已核验同一 Punch RP 的 UR3 接近数值零，未发现当前已保存结果内非预期旋转。轴对称刚体转动是 r–z 平面里的模式，不应描述成已观测到真实三维偏心倾斜。

试样顶/底外环夹持：JNL 807–816 的两个集合均 U1=U2=0；INP 集合成员解析证实夹持范围是 r≈0.002–0.005，分别位于 z≈0.0005 和 z=0，各 16 个节点。并非将整个试样体积固定。

值得警惕的命名问题：体区域集合 `set_specimen_clamped` 实际覆盖内区 r=0–0.002，`set_specimen_contact` 反而覆盖外区 r=0.002–0.005；两者名称与几何意图可能相反。但当前真实 BC 引用的是 `_clamped_top/bot` 边集合，解析结果在外环，不能因误导性名称便断言当前夹持设置反了。未来参数化若仅靠名字选区，存在误用风险。

**试样轴线 r=0 没有独立 U1=0 BC**。实际轴线 U1 非严格零；应在下一次模型修订前确认轴线边界需求。Abaqus 不自动为轴线节点加径向约束，见 [原厂轴对称单元约定](https://abaqus.uclouvain.be/English/SIMACAEELMRefMap/simaelm-r-axisymelem.htm)。本轮未自动补约束。

## Interaction / Surface selection

JNL 731–739：hard normal contact，允许分离；penalty isotropic friction，μ=0.1，允许弹性滑移比例 0.005。没有粘结或 no-separation 定义。

JNL 740–747 初始以匿名 Region/掩码定义 main/secondary；随后创建和重命名多个表面，793–799 将交互改为命名面：Punch `surf_punch_contact` 为 main，Specimen `surf_specimen_top` 为 secondary，finite sliding / surface-to-surface。当前 INP 的 Contact Pair 与此一致；Journal 的早期 mask 不能单独证明当前面选择。

依据 INP 单元 CAX4 的 S1–S4 连通边实际解析：

| 表面 | 面片数 | r 范围 | z |
| --- | ---: | --- | --- |
| surf_specimen_top（实际接触 secondary） | 66 | 0–0.005 | 0.0005 |
| surf_specimen_contact_top | 51 | 0–0.002 | 0.0005 |
| surf_specimen_contact_bot | 51 | 0–0.002 | 0 |
| surf_specimen_clamped_top | 15 | 0.002–0.005 | 0.0005 |
| surf_specimen_clamped_bot | 15 | 0.002–0.005 | 0 |

因此实际接触 secondary 是整个顶面，包含夹持外环，不是底面或竖边；不同子区因单元连接方向不同使用 S2 或 S4，但解析后的物理 z 相同。Punch 初始半径约0.00125，小于夹持起点0.002，实际接触压力也存在；未发现将试样底面误配为接触面的证据。整个顶面是否是最终设计意图、变形后的接触分布是否合理，仍需要模型/网格验证，不能仅凭这些检查宣称接触完全正确。

DAT lines 132–136 记录求解器将不兼容解析刚体主面的 path-based tracking 改为 state-based tracking。必须以实际执行的回退算法解释该次计算，而非按 JNL 的 TWO_CONFIG 请求宣称所请求算法被完整采用。

## Mesh 与 Output

- JNL 817–820 为 structured QUAD；821–825 先设大于几何量级的 bias 尺寸0.1/0.01，随后删除 seeds，830–834 改为 maxSize=0.0001、minSize=1e-5，不能沿用被删除的大尺寸。
- JNL 836–840 初始边尺寸0.0001，随后再次删除；843–850 改为0.0002。选边掩码没有 replay，最终实际网格以 INP/ODB 为准。
- JNL 852–856 的候选类型为 CAX4/CAX3；实际 INP/ODB 全部为 594 个 CAX4，没有 CAX3，也不是 CAX4R。试样670节点；从连通性解析的 [网格与表面图](input_geometry_audit.png)只展示真实未变形输入。
- JNL 715–723 及 INP 输出定义包含 S、PE、PEEQ、LE、U、RF、CSTRESS、CDISP；History 能量8项及 Punch RP U2/RF2。ODB 内实际有这些主变量并有 UR3/RM3；History 本身没有 UR3/RM3，转动核验使用 Field。
- 未进行网格收敛、完整变形网格质量或接触局部场空间检查；未以 594 个单元数量判定网格已充分。

## 证据冲突汇总

| 发现 | 采用的判定 |
| --- | --- |
| Journal 初始 UR3 未约束，后续固定 | 依据顺序与当前 INP，最终固定；不把早期未约束延续到当前 |
| Journal RP/草图/seeds 多次删除重建 | 只按后续状态及 INP 交叉核对；不执行 Journal |
| Journal Job 消息属于凌晨旧计算，当前 ODB 属于晚间计算 | Journal 是历史过程佐证；当前计算以同目录 INP/ODB/日志为准 |
| 两个同名 Job | 输入哈希相同、ODB时间和哈希不同；分别读取、比较，不拼接 |
| 命名的体集合与几何区域可能相反 | 真实边界集合及坐标优先；标记未来参数化风险 |
| 请求 contact tracking 与实际执行不同 | 采用 DAT 记录的 state-based 回退 |
| 材料表数字可被接受，语义未证实 | 保留物理定义 NOT VERIFIED，不静默转换 |

当前 CAE 最终状态、单位声明、材料来源与本构转换仍需进一步核查。本轮未读取 REC 作为模型真相，REC/COM/IPM/PRT 仅列入文件清单。
