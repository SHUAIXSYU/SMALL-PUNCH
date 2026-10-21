# 候选 Hollomon 材料表生成器

状态：**候选实现，未获物理验证**。run_007 授权开发离线参数化与测试，不授权修改 Sanity 模型或启动求解。文献 ε 的真实应变定义仍待确认。这里明确采用真应力–真总应变分段模型；不能把软件测试通过解释为文献测度、材料范围或 SPT 模型已经验证。

## API 和单位

实现：[inverse/hollomon.py](../inverse/hollomon.py)。仅依赖 Python 标准库，不依赖 Excel、Abaqus 或 SciPy；无文件写入、Job 创建或 Solver 调用。

```python
from inverse.hollomon import generate_hollomon_table

table = generate_hollomon_table(
    sigma_y_mpa=200.0,
    n=0.1,
    max_plastic_strain=0.9,  # run_007 的候选覆盖范围，并非所有未来参数的保证
    relative_tolerance=1e-3,
)
rows = table.rows  # ((Yield Stress [Pa], Plastic Strain [-]), ...)
fragment = table.abaqus_plastic_text()  # 仅返回 *Plastic 片段文本，不写文件
stress_pa = table.interpolate(0.01)    # 超出覆盖范围会报错
```

- 固定 E=210 GPa=`210e9 Pa`，ν=0.3。调用者必须在未来配套弹性定义中使用一致数值。
- 输入 `sigma_y_mpa` 明确为 MPa，固定乘 `1e6` 得到 Pa。不得传入 Pa 数值却使用 MPa 参数名。
- 输入 n 满足 `0<n<1`。本接口不将 n=0 理想塑性或 n=1 退化关系隐式视为常规硬化；两者均报错。
- `max_plastic_strain` 是无量纲等效塑性应变上限，必须显式传入。不是总应变上限，不随 mm/m 单位制缩放。
- 非有限值、非正屈服强度、非法容差、布尔值/字符串和无效点数预算报错。极端不可分辨数值范围会报错，不返回不完整表格。
- `relative_tolerance` 默认0.001，`absolute_tolerance_pa` 默认0；至少一个须大于零。`max_points` 默认10000；达不到精度就抛出 `SamplingError`。
- 表首点严格为 `(sigma_y_mpa*1e6,0)`。输出文本使用17位有效数字，使 Python 浮点值回读保持一致。
- `stress_from_total_strain(epsilon,sigma_y_mpa,n)` 返回完整单轴分段模型的 Pa 应力；`stress_at_plastic_strain(p,sigma_y_mpa,n)` 返回解析模型数值求根结果。
- 所有结果显式标记 `model_id='candidate-true-total-hollomon-v1'`、`physically_validated=False`。

## 数学契约

采用 σ=Eε（ε≤εy）和 σ=E εy^(1−n) ε^n（ε>εy），其中 εy=σy/E。

塑性阶段令 r=ε/εy≥1，则：

\[
\sigma=\sigma_y r^n,\qquad
p=\varepsilon-\sigma/E=\frac{\sigma_y}{E}(r-r^n).
\]

对于0<n<1，p随r严格增加，可以唯一反解。程序以 t=log(r) 计算：

\[
p=\varepsilon_y e^{nt}\operatorname{expm1}((1-n)t),
\]

以减小近屈服处相减的消减误差。该表达式严格来自扣除当前弹性应变，没有使用固定 ε−εy 代替 p。

该转换依赖单轴单调标定、小弹性应变和常规 J2 塑性假设；不是任意有限变形测度的通用加法，也不能把 SPT 中任意应变分量直接等同 PEEQ。材料泊松比、硬化类型及其他行为需要在未来模型中明确配套。

## 自适应插值与误差

Abaqus 硬化表在塑性应变坐标上作线性插值，所以直接控制 σ(p) 的插值误差。该候选曲线是递增凹函数，其导数为：

\[
\frac{d\sigma}{dp}=\frac{En}{e^{(1-n)t}-n}.
\]

每个区间计算割线斜率 m，通过 `dσ/dp=m` 定位绝对弦误差的唯一内部最大点，再在该位置分裂区间。接受条件为：

\[
\max(\sigma-\sigma_{linear})\le a_{tol}+r_{tol}\sigma_{left}.
\]

因为区间内 σ≥σleft，此条件保守地满足所有点的混合绝对/相对容差。计算在双精度中进行；不能分辨极值点时显式失败。返回值分别报告最大绝对弦误差、保守相对上界和归一化预算上界，不把有限密采样最大值声称为严格全区间最大值。

即使输出关系在节点处恢复原分段模型，点间仍是受控数值近似。此误差不等于有限元误差、F–D预测误差或物理模型误差。

## 覆盖范围

`suggest_plastic_coverage(observed_max_peeq, safety_factor=1.25, round_step=0.1)` 提供显式工程余量规则：完整历史 PEEQ 最大值乘1.25，再按0.1向上取整。零塑性历史无法支持塑性覆盖范围，函数会拒绝该输入。

run_007 根据现有 ODB 所有保存帧的积分点 PEEQ，建议样例覆盖 `0≤p≤0.9`。来源、峰值位置和处理明细仅在 Run 私有审计区。未从 PE、LE 的单个分量猜测等效塑性应变，也未用百分位数排除最大值。

这是旧材料和旧载荷下已保存输出的数值覆盖建议。新参数会改变应变场，未保存的增量也没有被本次扫描覆盖。后续任何获准求解都需检查新 PEEQ 最大值并按需要重新生成范围；不能宣称0.9内材料已获实验验证。库内查询超界时报错，但实际 Abaqus 可能采用其表格外规则，因此不能仅靠 Python 检查防止未来求解超界。

## 已执行测试与样例

在仓库根目录执行，解释器路径显式指定：

```powershell
& 'D:\XianLab\envs\conda\torch-gpu\python.exe' -B -m unittest discover -s tests -p test_hollomon.py -v
```

标准库 unittest 避开既有 pytest/iniconfig 缺失，不安装新依赖。测试覆盖闭式 n=1/2 独立解、完整弹性与屈服衔接、当前弹性应变扣除、单调性、非法输入、自适应误差、精度与点数预算、禁止静默外推和输出精度。

回归样例参数为200 MPa、n=0.1，覆盖至p=0.9，共35行；独立 SciPy Brent 求根验证14859点，最大采样相对误差约0.09504%，保守全区间相对上界约0.09646%，小于0.1%目标。25组数值组合检查亦通过，不代表材料参数先验或实验验证。

- [材料表 CSV](../run/run_007/artifacts/candidate_Q200_n01_plastic.csv)
- [仅 *Plastic 的候选片段](../run/run_007/artifacts/candidate_Q200_n01_plastic.inc)，不是完整 Job 输入，未提交求解
- [机器可读误差报告](../run/run_007/artifacts/error_report.json)
- [Run 总结与私有对照入口](../run/run_007/summary.md)

常规输入与插值规则参考 [Abaqus Defining plasticity](https://abaqus.uclouvain.be/English/SIMACAEGSARefMap/simagsa-c-matdefining.htm)。原模型定义未修改；本候选文档不覆盖已有文献未决项。
