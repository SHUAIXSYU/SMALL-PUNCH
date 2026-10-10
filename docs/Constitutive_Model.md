# Hollomon 本构技术契约

状态：技术说明，正式材料表生成暂缓。当前只识别 `sigma_y` 和 `n`，`E` 保持可扩展的已知参数接口。

## 应力应变定义

| 量 | 定义或含义 | 约束 |
| --- | --- | --- |
| Engineering stress | F/A0，初始面积归一 | 不能直接替代 true stress |
| Engineering strain | (L-L0)/L0 | 不能直接替代 logarithmic strain |
| True stress | F/A，瞬时面积归一（Cauchy stress） | Abaqus 常规金属塑性输入应力量 |
| True total strain | 单轴均匀变形下 ln(L/L0) | 包含弹性和塑性贡献 |
| Plastic strain | 单轴小弹性应变假设下 epsilon_total − sigma_true/E | 不能统一减去常数 sigma_y/E |
| Equivalent plastic strain | J2 关联塑性下的累积标量，常以 PEEQ 表示 | 不能将任意总应变或某个塑性应变分量直接等同它 |

在经典 J2、塑性不可压缩的约定下，累积等效塑性应变可写为积分 `∫sqrt((2/3) dεp:dεp)`。单调单轴标定时可用相应单轴塑性应变建立硬化曲线；复杂加载路径中它是路径累积量。

## 候选公式与连续性

弹性段：`sigma = E * epsilon`。一般 Hollomon 形式：`sigma = K * epsilon^n`。这两式本身尚未说明 epsilon 是工程、真实总应变还是塑性应变，不能直接产生 Abaqus 输入。

原始资料图中可辨认的分段形式为：

```text
epsilon_y = sigma_y / E
sigma = E * epsilon                              epsilon <= epsilon_y
sigma = E * epsilon_y^(1-n) * epsilon^n           epsilon > epsilon_y
K = E * epsilon_y^(1-n) = E^n * sigma_y^(1-n)
```

K 的等价关系由上述分段式代数推出；仅在采用同一应变定义及连续屈服约定时成立。此时 K 不应再独立于 sigma_y、n、E 自由变化。图像是裁剪资料，公式中的应变测度、完整文献和适用条件尚未核验，不据此批准正式模型。

若另一来源使用 `sigma = K * (epsilon_plastic)^n`，它与上述总应变分段式不同；n>0 时在零塑性应变处给零应力，与有限初始屈服应力不直接相容。需要明确偏移、截断或其他屈服衔接规则，不能悄悄替换为 Swift/Ludwik 等模型。

## Abaqus 输入约束

常规各向同性金属硬化 `*Plastic` 通常输入 true yield stress 与 equivalent plastic strain，首点塑性应变为零。单轴总应变应扣除当前 `sigma_true/E`。工程数据仅在均匀、颈缩前且相应体积近似成立时采用 `sigma_true = sigma_eng*(1+epsilon_eng)`、`epsilon_true = ln(1+epsilon_eng)` 转换。以上依据 [Abaqus 原厂用户文档的高校镜像：Defining plasticity](https://abaqus.uclouvain.be/English/SIMACAEGSARefMap/simagsa-c-matdefining.htm) 与 [Inelastic behavior](https://abaqus.uclouvain.be/English/SIMACAEMATRefMap/simamat-c-plastic.htm)。查阅日期为 2026-10-10；2024 文档 URL 获取返回 403，镜像内容不替代未来对实际安装版本和所选硬化选项的核验。

SPT 的力–位移不能直接按单轴公式换成材料应力–应变。转换要基于明确的单轴标定定义或批准的本构公式。未来生成器必须验证单位、有限值、应变顺序、零塑性首点、屈服衔接、硬化趋势、取样范围与外推规则。未批准的输入不得自动修正后使用。

## run_001 差异登记

- `CM-001`：公式图给出上述分段形式，但应变测度及完整文献来源未明确。另一曲线图标注 true stress/true strain；不能仅因此认定它与公式图、Excel 是同一完整契约。
- `CM-002`：工作簿抽查公式使用 `epsilon − sigma_y/E` 型固定偏移。如果该列意图作为塑性应变，它与 `epsilon − sigma(epsilon)/E` 不一致。列含义尚未确认，因此登记为待澄清差异，不宣判所有表格数据错误，也不修改公式。
- `CM-003`：参数截图和工作簿中的示例不能直接成为正式材料参数、反演边界或实验真值。

私有来源文件名、单元格和公式证据保存在 run_001 的忽略审计区。没有生成正式材料表，没有统一不同来源的公式。解除限制需要确认应变定义、列用途、完整文献、E/单位、屈服定义以及材料表转换方案。
