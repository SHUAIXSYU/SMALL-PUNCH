# run_006 — Hollomon 文献、Excel 与材料定义一致性

状态：**WARNING**。只读来源分析与独立数值核验完成；正式材料模型的应变测度和适用范围仍需合作方确认。

## 实际结果

- 工作簿全部参数组的应力公式与给定文献的塑性段代数等价，独立数值对照及屈服连续性检查通过；工作簿并未实现完整弹性分支。
- 在文献自变量为真总应变的假设下，固定减去屈服应变不能替代扣除当前弹性应变。两者差值为 `(sigma-sigma_y)/E`；前者对应另一个带偏移的塑性硬化模型。
- 当前 INP 材料表逐行复现工作簿派生列并补入屈服首点，保留了应变定义、非恒定应力缩放与近屈服采样问题。单位转换、应变定义和插值误差分别量化，没有混为一项。
- 完成 A 文献总应变曲线、B 当前派生曲线、C 真总应变假设下正确换算曲线及对比图。独立诊断数据不是批准投入模型的正式材料表。
- 图像资料支持参数角色，另有真应力/真应变标注，但裁剪来源不足以严格确认完整文献契约。没有据此给出已验证材料范围或反演边界。

## 证据和隐私

完整 [中文报告](artifacts/private/hollomon_consistency_report.md)、[数值核验](artifacts/private/numerical_audit.json)、[比较图](artifacts/private/hollomon_comparison.png) 和独立 CSV 位于 Git 忽略的私有审计区。源路径、参数原值、单元格公式及来源明细没有放入公开摘要。源文件没有复制、移动或修改，也没有上传。

文件索引与 SHA-256 见 [manifest](artifacts/manifest.json)；最终完整性和 Git 检查见 [final_state](checkpoints/final_state.json)。私有证据不会随 Git clone 分发，缺失时应说明，不能据公开摘要重建原始数据。

## 执行与验证范围

使用用户指定 Torch-GPU 解释器。Excel 只读解析公式与缓存值，未重算或保存工作簿；全部公式递归算术检查、独立幂律数值计算、屈服点及额外采样检查、INP 格式化逐行对照、诊断曲线单调性和总应变重建检查均已执行。图已生成并目视检查。源码和模型完整性以执行前后 SHA-256 验证。

先读取实际 AGENTS、项目状态、Run 协议和最近 Run，记录 Git branch/HEAD/remote/working tree，再独占创建本 Run。仅新建本 Run 并更新 Run 索引/项目状态，保留既有用户改动。没有改动 Excel、CAE、INP、旧 Run、AGENTS 或依赖环境；没有打开 CAE API、读取新 ODB、启动 Solver、提交 Job、训练 RL、commit 或 push。

既有 pytest/iniconfig 依赖警告保留，不调用 pytest、不安装依赖。本轮数值脚本直接执行成功。PASS 只适用于列明的数学/读取/完整性检查；物理材料准入仍为 WARNING。

## 后续需要

合作方确认文献测度和材料有效范围后，再另行授权选择明确的参数化契约、修订模型和验证采样精度。若选择真总应变分段关系，可用 `r=epsilon/(sigma_y/E)`、`sigma=sigma_y*r^n`、`p=(sigma_y/E)*(r-r^n)` 生成一致的单轴硬化数据；这不是本轮对正式材料模型的批准。当前指令已完成，停止，不自动进入下一 Run。
