# Agent 文件通信与 Run 协议

## Run 登记

每次独立研究产出登记 `run/run_XXX/`，至少三位递增编号，不复用。先查索引并独占创建目录；同一编号发生竞争则停止。`run/README.md` 记录所有 Run 的目标、状态及 summary 链接。

每个 Run 必须有 `run.json`、`summary.md`、`artifacts/`、`checkpoints/`。Run 保存过程与结果索引，模型在 CAE，研究数据在 experiments，大型作业输出在忽略的 CAE/Jobs。相对路径均以仓库根目录为基准；Markdown 链接按文档所在目录解析。

## run.json v1

| 字段 | 类型与语义 |
| --- | --- |
| schema_version | 字符串，目前 1.0 |
| run_id | 字符串，与目录名一致 |
| stage | 字符串，研究阶段 |
| objective | 字符串，本次具体目标 |
| status | RUNNING / PASS / WARNING / BLOCKED / FAILED |
| start_time / end_time | ISO 8601 带时区；无法确定为 null，并写 time_notes |
| python_interpreter | 字符串，实际选定解释器；未找到为 null 并 BLOCKED |
| git_head / git_branch | 执行基线，不暗示改动已提交 |
| inputs | 对象数组：path、role、可选 sha256；私有详情使用本地清单引用 |
| outputs | 对象数组：path、role；不得把未生成文件写为结果 |
| validation | 对象数组：check、status、evidence、scope |
| errors | 对象数组：code、severity、message、evidence、resolution；没有则 [] |

输入/输出路径必须保持在仓库内，不允许 `..` 穿越、绝对工作路径或越界链接。python_interpreter 属工具定位元数据例外，不是输出路径。私有证据不随 Git clone 分发，缺失时如实说明，不能凭公开摘要重建原始数据。

状态转换：RUNNING → PASS/WARNING/BLOCKED/FAILED。PASS 表示声明范围全部满足；WARNING 表示工作已完成但有未决风险或研究前提；BLOCKED 表示关键执行条件缺失无法完成；FAILED 表示执行/验证失败。UNKNOWN 用于字段事实，不能作为成功状态。不得把作业成功与研究有效性混用。

## 写入、检查点和交接

本文件规定 Run 文件交接约定，不实现通用文件队列。run_008 另建项目专用 SQLite AgentHub，完成角色身份、事务 claim、lease、消息和审计；它不改变此处既有 Run 元数据规则。更新 JSON 在同目录写临时文件、校验后原子替换，并保留前一检查点。原始资料永不适用覆盖更新规则。检查点记录时间、阶段、输入/输出哈希、Git 状态和恢复条件，不放模型训练权重或大型求解数据。

artifacts/manifest.json 优先记录实际文件的仓库相对路径、角色、公开性及可用校验值。哈希不对自身或持续更新的 run.json 形成循环依赖；最终静态文件可另记哈希。原始资料清单本地保存，公开只保存数量和核验结论。

summary.md 必须说明任务、实际动作、发现、修改文件、验证、阻塞和下一 Run 建议。接手 Agent 先核对状态和证据，再处理建议；建议不是自动执行授权。失败诊断保留命令、返回码、环境版本及日志引用，敏感路径放私有日志。重试另记 attempt，不覆盖旧结果。

run_001 的所有时间和版本以本机/工具实测为依据，未进行 Solver、许可证签出、CAE 打开或模型验证。重现实验还需要源数据及 FE 输入，当前基础架构不宣称已具备科学结果复现能力。
