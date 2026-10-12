# Existing ODB 只读审计

结论：**ODB 提取范围 PASS；数值与物理可信度 WARNING。** 本次使用 Abaqus 2024 自带 Python 3.10.5 / `SMAPython.exe`，以 `openOdb(path=..., readOnly=True)` 打开现有 ODB；返回 `isReadOnly=true`。没有升级、保存、求解或提交作业。

## 文件身份与完成状态

- 主审计对象：用户指定 Sanity 模型目录的 Job-1.odb；同目录存在 INP、STA、MSG、DAT、LOG、CAE 和 JNL。完整 24 个文件的路径、大小、修改时间、SHA-256、角色及来源见 [私有清单](private/file_inventory.json)；[公开清单](file_inventory.json)保留数量与证据入口。
- Sanity ODB 创建时间由 ODB 自报为 `2026-10-12T18:17:12+08:00`；同组 LOG 记录 Input Processor 于 18:17:04 开始、Standard 于 18:17:13–18:20:24 运行、18:20:25 完成。LOG 本身无时区；这里的日志时间保留本地文本语义，以带 GMT+08:00 的 ODB 时间作关联，不将文件 mtime 当作求解耗时。
- ODB 版本 `Abaqus/Standard 2024`，单精度；诊断状态 `JOB_STATUS_COMPLETED_SUCCESSFULLY`、0 errors、6 analysis warnings。STA 明确成功结束，DAT/LOG 同样记录完成。DAT 的 1 条警告、MSG 的 51 条警告与 ODB 的 6 条诊断警告是不同计数口径，未强行统一。
- INP 与 ODB 的 670 个试样节点、594 个 CAX4 单元逐项核对：连接关系一致，坐标最大差 `4.995e-12`（INP 十进制写出精度范围）。Step 名称、时长、RP 集合、位移及输出请求相符。由这一组证据选定身份，而非仅按 mtime 选最新文件。
- TempTry 是独立历史比较对象：其 INP 与 Sanity 的 SHA-256 完全相同，但 ODB 的 SHA-256 不同、创建时间为 `2026-10-12T00:54:03+08:00`。两组结果分别读取；Sanity CSV 未混入 TempTry 数据。

## ODB 结构

| 项目 | 实测内容 |
| --- | --- |
| Step | `Step_Punch_Displacement` |
| Procedure | `*STATIC`，`nlgeom=True` |
| Step timePeriod | 1.0，实际保存范围 0–1 |
| Step totalTime | 0.0，表示该 Step 开始前累计时间，不能误当本 Step 时长 |
| Frames | 181，包含初始帧和 180 个收敛增量 |
| History Regions | `Node ASM_SPT.1`；`Assembly ASSEMBLY` |
| RP history | U2、RF2，各 181 点 |
| Assembly history | ALLAE、ALLFD、ALLIE、ALLPD、ALLSD、ALLSE、ALLWK、ETOTAL，各 181 点 |
| Instances | `ASM_SPT`：AXISYMMETRIC / ANALYTIC_RIGID_SURFACE，1 node；`ASM_SPT-1`：AXISYMMETRIC / DEFORMABLE_BODY，670 nodes、594 CAX4 |
| Assembly Node Sets | ` ALL NODES`；`REFERENCE_POINT_ASM_SPT        1` |
| Assembly Element Sets | ` ALL ELEMENTS` |
| Punch Node Sets | SET_PUNCH_RP（node 1）；无 Punch Element Set |
| Specimen Node / Element Sets | SET_SPECIMEN_ALL、SET_SPECIMEN_CLAMPED、SET_SPECIMEN_CLAMPED_BOT、SET_SPECIMEN_CLAMPED_TOP、SET_SPECIMEN_CONTACT |
| Field outputs | AC YIELD、LE、PE、PEEQ、RF、RM3、S、U、UR3，以及带接触对限定名的 COPEN、CPRESS、CSHEAR1、CSLIP1 |

所有集合成员、节点坐标、单元连接、Frame 元数据、History 描述及完整数据保存在 [只读导出](private/odb_extract_attempt03.json)，无需复制原始 ODB。

## Punch RP 与符号核验

INP lines 1372–1383 将 `ASM_SPT` 关联到 `part_punch`，`ASM_SPT-RefPt_` 与 `set_punch_rp` 均包含 node 1，`*Rigid Body` 明确引用该节点集合与 `surf_punch_contact`。ODB 同一实例的 SET_PUNCH_RP 也仅含 node 1，History 描述直接指向该实例、节点及集合。因此 U2、RF2 来自同一真实 Punch RP。

INP lines 2684–2687 对 RP 施加 U1=0、U2=−0.0012、DOF6=0；没有节点坐标变换。采用向下压入为正的机械约定：

```text
displacement = -U2
force = -RF2
```

原始 RF2 与 U2 在加载段均为负，RP 轴向反力与试样支承反力方向相反；总轴向反力的最大残差为 0.06694 个模型力单位，约为峰值力的 0.00886%。这支持以 `-RF2` 表示向下施加的压入力。未使用绝对值、平移基线或额外 2π 系数。轴对称节点力采用整圆合力约定，参见 [Abaqus 原厂手册高校镜像：Axisymmetric solid element library](https://abaqus.uclouvain.be/English/SIMACAEELMRefMap/simaelm-r-axisymelem.htm)。此处转换建立了模型压入正方向，并不等于已经核验某台实验机的符号与单位。

单位声明 **NOT VERIFIED**：输入数值与 m–N–Pa 体系相容，但 JNL/INP/ODB 无明确单位声明，不能仅凭数值大小作事实认定。CSV/图均标注模型长度、力和时间单位；若以后确认 SI，则末位移约 1.2 mm、末力约 755.893 N。静力 Step 的时间是加载参数，不能据此认定实际加载速度。

## 真实曲线与交叉校验

| 项目 | 结果 |
| --- | --- |
| 原始 U2 末点 | −0.0012000000569969416 |
| 原始 RF2 末点 | −755.8928833007812 |
| 正向压入位移末点 | 0.0012000000569969416 |
| 正向力末点 / 已保存范围峰值 | 755.8928833007812 |
| 样本与插值 | 181 点；U2/RF2 的时间轴精确相同，不需要插值 |
| Field vs History | RP U2 与 RF2 逐点差均为 0；Frame time 与单精度 History time 以 1e-7 容差匹配，无重采样 |
| 线性加载误差 | 相对 INP `U2=-0.0012*t` 的最大绝对差 5.924e-11 |

结果：[原始 CSV](punch_rp_history_raw.csv)、[正向 CSV](punch_force_displacement.csv)、[U2–time](punch_u2_time.png)、[RF2–time](punch_rf2_time.png)、[Force–Displacement](force_displacement.png)。这些是模型结果，不是实验曲线，也不是材料反演结果。

## Numerical sanity

1. **加载、反力和跳变**：位移单调，已保存反力没有反向或下降；但曲线存在局部陡增/折点，不能描述成完全平滑。尤其增量 159→160，位移从 0.0007714294 到 0.0007737826 时，力增 11.6865，局部割线斜率约 `4.966e6`，全程割线斜率中位数约 `6.886e5`。该位置接近增量 160 的 cutback/畸变记录；相关性不证明物理原因。最大相邻力增量 38.3157 出现在较大的位移步长 `6.4402e-5` 上，不能单凭此值判为异常。缺少网格/增量敏感性结果，折点来源仍 NOT VERIFIED。
2. **接触建立**：由解析 Punch 轮廓及装配平移，初始最低点与试样顶面在名义几何上相接。初始帧 CPRESS=0；第一个保存的正时间点 `t≈0.0025` 已有正 CPRESS 和非零 RF2。因此接触建立位于初始至首个收敛点之间，精确时刻无法由现有采样确定。首点局部 CPRESS 最大约 `9.294e8`，末点约 `4.962e8`（模型应力单位）；应力尺度与局部离散敏感性尚待核查，未凭压力值宣称接触正确。
3. **接触间隙数据**：COPEN 含 `−3.402823e38` 级异常哨兵值。原始极值仍保留；单独统计有效间隙时排除非有限值及绝对值大于 `1e30` 的值，未把它们视作巨量穿透。末帧 67 个值中排除 25 个，剩余范围约 `−2.389e-8` 至 `−3.474e-9`。该诊断阈值是识别非物理占位值的处理规则，不是接触容差验收标准。
4. **转动**：轴对称刚体具有 1、2、6 自由度，不能假定它没有旋转模式。[原厂手册：Rigid body definition](https://abaqus.uclouvain.be/English/SIMACAEMODRefMap/simamod-c-rigidoverview.htm)。当前 RP 的 U1 最大绝对值约 `5.993e-34`，UR3 约 `3.839e-35`，支持已保存帧内固定径向运动和旋转。末点 RF1≈599.373、RM3≈−0.89794 是约束反力/矩，不能当作实际侧向倾斜证据，也不能与轴向 RF2 混合。
5. **轴线约束**：INP 未对试样 r=0 节点显式施加 U1=0；ODB 中轴线节点的最大径向位移约 `8.315e-8`。这不是自动约束后的严格零值。Abaqus 不自动施加轴线边界条件，非线性分析中应审查其必要性；依据同上轴对称单元手册。当前小数值不证明轴线定义已合格。
6. **收敛与畸变**：180 个接受增量、45 次失败尝试；MSG 51 个 warning headers，其中 38 次大应变增量、4 次负特征值、3 次塑性计算未尝试、4 次过度畸变、2 次零力矩提示。负特征值发生于 `(increment,attempt)=(1,1),(114,1),(123,1),(160,2)`；4 次畸变警告位于 `(1,1),(114,1),(160,1),(160,2)`。全部对应 STA 的失败 U 尝试，随后减小步长并继续收敛。不能把这些试算态直接认作最终收敛网格已经失效，也不能忽略其数值敏感性信号。最终最大 PEEQ≈0.68857；完整收敛态网格质量/Jacobian 审查 NOT VERIFIED。
7. **能量**：ALLAE、ALLSD 均为 0；末点 ALLIE≈0.535501、ALLPD≈0.533178、ALLSE≈0.00232276、ALLFD≈0.00896148、ALLWK≈0.546329、ETOTAL≈−4.90050e-5（模型能量单位）。按真实 RP 采样用梯形积分得到 `∫F dd≈0.546329207`，与 ALLWK 绝对差约 `6.636e-8`。存储的 ETOTAL 最大绝对值 / 末点 ALLWK≈0.00902%，仅为本次量级诊断，不是预定验收阈值。缺少 ALLCCE、ALLCCDW 等接触能量项，不能独立重建完整能量平衡；简单 `ALLIE+ALLFD+ALLSD−ALLWK` 的 −0.00186696 不等于 ETOTAL。参见 [Abaqus 能量变量定义](https://abaqus.uclouvain.be/English/SIMACAEOUTRefMap/simaout-c-std-wholeandpartialmodelvariables.htm)。结果见 [energy_history.csv](energy_history.csv) 和 [能量图](energy_diagnostics.png)。

详细数字、警告上下文和历史对比见 [numerical_sanity.json](numerical_sanity.json)、[field_diagnostics.csv](field_diagnostics.csv)、[私有日志解析](private/log_analysis.json)。

## 执行故障与证据边界

首次脚本已读取 ODB，但导出 JSON 时因 Abaqus 返回 float32 导致序列化失败；失败控制台与脚本保留。Abaqus 批处理包装返回 0，不能据此视为成功。第二次显式转换数值标量后成功；第三次增加 RP UR3/RM3 与 COPEN 有效值统计，前次结果保留。以实际 JSON `status`、`isReadOnly`、数据断言及原始文件哈希作为成功依据。

一次 PowerShell Get-FileHash 对正在被其他进程共享的 JNL 返回占用错误；随后只读 Python 读取并核对 SHA-256 与基线一致，未强制解锁或改动文件。2024 在线手册部分页面返回 403，通用约定引用原厂手册高校镜像；不将其冒充本轮 Abaqus 2024 特定功能运行验证。
