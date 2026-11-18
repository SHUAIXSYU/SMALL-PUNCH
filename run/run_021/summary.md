# run_021 — run_020 四点 Queue-only 入队

**WARNING / FOUR_JOBS_QUEUED_AWAITING_MANUAL_START**

用户授权的四个冻结输入已经通过公开API按L01→L04入队，每项14 CPU、0 GPU、Datacheck=True、Full=True、最多一次尝试/零自动重试。中心不重算；没有其他可执行任务。Solver和Datacheck均未启动，科学分析尚未发生。

|顺序|Job|queue_id|状态|
|---|---|---|---|
| 1 | SPIO_R020_L01_SYM | `q_7158d0dad2bd46199a24799701899cf0` | QUEUED |
| 2 | SPIO_R020_L02_SYP | `q_9c905ac50611446eb4bb828619eb8a2f` | QUEUED |
| 3 | SPIO_R020_L03_NM | `q_6e02167dcd0b494ca07c847c7909c86c` | QUEUED |
| 4 | SPIO_R020_L04_NP | `q_bbaaeda7491a4a60b237879bd755c247` | QUEUED |

AgentHub正式任务：`9e9d031b-b7b9-4540-8819-1af81b9e41d1`。授权、请求、实际Queue、输入身份、资源、预览和结果已登记；MAIN读回任务及证据，未声称自动跨会话唤醒。

## 已执行的核验

- Project ID完全一致：b87d2cd6-8519-4ac3-bae6-7eb989fb2dae。Settings严格返回PERSISTED，Abaqus2024命令文件存在，14/0资源、两阶段开启、自动关机关闭。
- 四个完整INP/参数hash匹配冻结清单，独立工作目录为空，无外部引用依赖；四项Preflight/Dry-run全部通过。当前Runner所有权ABSENT、live状态IDLE，无目标Solver进程或恢复冲突。
- 入队前无既有四点记录，入队后四个唯一queue_id顺序正确且时间字段未启动；两条历史已完成记录未变。实际入队使用显式JobRequest和公开API，官方runtime事务防止GUI在批次入队间取得所有权，未直接写Queue/DB。
- 原输入、参数、Settings、ProjectDB、live_status及所审计外部源码保持hash不变。没有修改外部安装，没有生成第五个Job、重新计算中心或重试。

## 异常控制：AUTO_STOP_UNAVAILABLE

本机安装0.2.2，Git HEAD 7012133e7cc0176bb3e56fc24d7154ee3b90bb81、工作树干净。审计了该安装的GUI/Runner代码，并完成7项隔离Fake检查；没有真实Solver测试。核验时没有观察到正在运行的GUI进程，不能声称已绑定当前窗口；用户启动时应使用该安装并打开正确Project。

Datacheck失败会阻止**同一Job**继续Full，但Queue循环仍可执行下一Job。Full失败或COMPLETED_WITH_WARNINGS同样不会自动暂停整队列。Start Queue执行所有QUEUED/DATACHECK_OK项，界面选择/过滤不限制执行范围。Stop After Current Job只是循环边界标志，存在请求晚于检查的竞态；启动前设置还会被start清零，因此不是真正逐项审核门控。正常停止保留后续QUEUED任务；崩溃/关闭GUI不能保证终止活动Solver，可能留下需要恢复的执行状态。

**点击Start Queue可能连续执行全部四项，失败和严重警告不会自动阻断后续项。** 用户已允许在此限制下入队。本轮没有实现或宣称自动fail-stop。建议人工在场监控；如果需要保证每项审核后才能继续，应在实际启动前另行完善并验证受控逐项执行方式。不要依赖关闭GUI或临近边界点击停止作为可靠联锁。

## 交付和停止

通过GUI Open Project打开`E:\Projects\SMALL-PUNCH\agenthub_sp_invopt\abqjobpilot_project`。入队完成后已停止主动执行，由用户决定手动启动；不代点Start。原run_020逐项放行建议保留为历史，本轮依新授权一次性加入四项，但不把人工建议冒充Runner能力。

产物：[输入/资源与入队结果](artifacts/enqueue_result.json)、[本机Runner审核](artifacts/runner_audit.md)、[7项Fake结果](artifacts/runner_fake_tests.json)、[AgentHub登记](artifacts/agenthub_receipt.json)、[最终核验](artifacts/final_verification.json)。Run索引和项目状态更新；旧Run不改。

第6–9节的ODB提取、Loss和可识别性分析未执行，须待用户完成计算再据实际结果开展。未访问封存拉伸数据；独立数据保留验证，存在历史信息暴露。不commit/push。
