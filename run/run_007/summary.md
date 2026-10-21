# run_007 — 候选 Hollomon 材料参数化

状态：**WARNING**。候选生成器及数值验证完成；文献真实应变定义和物理材料有效性仍待确认，没有将软件测试通过标为最终物理验证。

## 交付

- [可复用生成器](../../inverse/hollomon.py)：纯标准库，输入 σy(MPa)、n，固定 E=210 GPa、ν=0.3，返回应力Pa/无量纲塑性应变。
- [接口与数学说明](../../docs/Hollomon_Material_Generator.md)。
- [单元测试](../../tests/test_hollomon.py) 与 [最终测试日志](artifacts/unit_tests_attempt02.txt)：11项通过。
- [候选材料表CSV](artifacts/candidate_Q200_n01_plastic.csv) 和 [仅 *Plastic 的片段](artifacts/candidate_Q200_n01_plastic.inc)：200 MPa、n=0.1，覆盖p=0.9，共35行。
- [误差报告JSON](artifacts/error_report.json) 与 [独立误差数据](artifacts/candidate_interpolation_error.csv)。
- [私有完整报告](artifacts/private/material_parameterisation_report.md)、[新旧对照图](artifacts/private/old_new_material_comparison.png)、[新旧对照CSV](artifacts/private/old_new_comparison.csv)、[ODB覆盖建议](artifacts/private/coverage_recommendation.json)。源路径、旧模型原值、峰值位置和来源明细保持在Git忽略区。

## 已执行结果

严格按 p=ε−σ/E 建立候选硬化表，MPa→Pa固定乘1e6。以σ(p)每段绝对弦误差的解析极值点自适应分裂，近屈服自动加密。节点总应变重建、屈服连续性、严格单调性、非法参数、输出单位、精度预算、超范围拒绝及序列化回读均有检查。

200 MPa、n=0.1回归样例在14859个独立验证位置的最大采样相对误差约0.09504%；保守全区间相对上界约0.09646%，均低于0.1%目标。25组数值组合检查通过，不是反演先验或实验验证。样例片段无Job、Step或提交命令。

使用Abaqus自带Python只读扫描既有ODB所有保存帧的积分点PEEQ；没有用PE或LE分量冒充等效塑性应变。按历史最大值加25%余量并以0.1向上取整，提出pmax=0.9。该建议仅用于初始数值覆盖；更改参数后必须重新检查，不表示材料已验证可用到该应变。

## 执行边界和失败记录

先读实际AGENTS、状态、最新Run和协议，确认007未占用后独占创建。开始时Git为main/e87aadc9f7074fc4bc127c9ae03afbe9081dabae；Sanity CAE的既有修改和REC的既有删除均保留，不恢复、不覆盖。

普通分析使用指定Torch-GPU Python，ODB API使用Abaqus自带Python独立进程，JSON交接。没有安装依赖；既有pytest依赖缺失保留，使用标准库unittest。

独立对照首次因极近屈服点的浮点求根包围失效而失败；扩大验证器上界后第二次通过。保留私有失败日志，没有将失败记作零误差。首次生成的相同样例内容只校验并复用。最终图已目视核验。

仅新增生成器、测试、候选说明及本Run，并更新Run索引/项目状态。源文件及旧Run完整性见 [最终检查](checkpoints/final_state.json)，产物哈希见 [manifest](artifacts/manifest.json)。没有修改Excel、CAE、INP；没有启动Solver/datacheck、生成或提交新Job、训练RL、commit/push或修改外部项目。

## 后续

确认文献测度、物理范围和材料模型约定后，再另行授权将候选表接入独立模型及进行受控求解。不得将当前候选样例自动替换Sanity材料表。本轮完成后停止，不自动进入下一Run。
