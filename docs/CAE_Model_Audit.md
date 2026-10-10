# run_001 CAE 与资料只读审计

审计范围：仓库中除 .git 外的既有文件，包括迁移前 Materials 和迁移后 references_private。起始仓库仅有 README 和 5 个原始资料文件，无 Python 源码、依赖清单或配置。新增的环境探针不属于原始 CAE 脚本。

| 原始文件类别 | 数量 | 核验深度 |
| --- | --- | --- |
| .cae / .inp / .odb / .jnl / .py | 各 0 | 递归文件清单，未发现这些扩展名 |
| .xlsx | 1 | ZIP/XML 只读结构及公式抽查，未重算、未导出 |
| .png | 3 | 人工视觉阅读，含公式、示例参数及应力–应变图 |
| .mp4 | 1 | 文件可读性、长度与 SHA-256；未播放或推断模型配置 |
| .csv / .xls / .pdf | 各 0 | 文件清单 |

没有确认可直接使用的实验力–位移数据。工作簿是含公式的参考表，其列语义和实验来源尚未验证。图像不等于可用于反演的机器可读曲线。

| 审计项目 | 状态 | 证据/限制 |
| --- | --- | --- |
| 本机 Abaqus 版本 | 已核验 Abaqus 2024 | 仅 information=release 查询 |
| 原模型创建版本 | UNKNOWN | 无 CAE/INP/ODB 文件 |
| Analysis step | UNKNOWN | 无模型输入 |
| Specimen geometry | UNKNOWN | 未从视频文件名推断 |
| Punch / die geometry | UNKNOWN | 无可核验模型 |
| Material definition | UNKNOWN | 有参考公式，不等于模型实际材料卡 |
| Contact and friction | UNKNOWN | 无接触定义 |
| Boundary conditions | UNKNOWN | 无模型输入 |
| Mesh / element type | UNKNOWN | 无模型输入 |
| Output requests | UNKNOWN | 无模型输入 |
| Load / displacement application | UNKNOWN | 无模型输入 |
| Force–Displacement extraction | UNKNOWN | 无 ODB、脚本或已确认提取区域 |
| CAE / Solver license and execution | UNKNOWN / NOT TESTED | 未启动 CAE 或求解 |

已对本机 Abaqus Python 做独立版本查询；实际版本记录在 run_001 summary。它不继承外部 torch-gpu 包可用性。版本命令的包装输出包含 JOB 字样，实际请求仅查询版本/解释器，没有提交 FE 求解。

模型审计的研究前提尚未满足，不能将本报告作为模型已通过核验的证明。详细来源与本构差异证据留在本地私有审计区；公开技术差异见 [本构契约](Constitutive_Model.md)。
