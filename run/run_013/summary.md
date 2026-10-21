# run_013 — Strict persisted Settings verification

**PASS（限工程执行链路预检查）。具备申请第一次新 Hollomon 候选模型单次正向求解授权的条件；没有授予或执行入队、Solver/datacheck启动。**

## 实际配置与身份

以修复后的公开 `AbqJobPilotClient.get_project_settings(project_id=...)` 严格查询 `b87d2cd6-8519-4ac3-bae6-7eb989fb2dae`，返回 `PERSISTED`、`persisted=true`、`exists=true`，`defaulted_fields=[]`。解析到的Project、Runtime和Settings路径与仓库专用Project完全一致，API原始值、磁盘JSON和effective_settings相同。

保存值：Abaqus `D:\ABAQUS2024\Commands\abq2024.bat`（文件存在并记录SHA-256）、CPU14、GPU关闭/0、Datacheck开启、Full Run开启、Auto shutdown关闭。查询没有创建或保存任何设置。

修复版仍声明0.2.2，实际源码HEAD为 `7012133e7cc0176bb3e56fc24d7154ee3b90bb81`，工作树干净；与run_012所用修复前HEAD不同，因此本Run重新执行公开API检查并记录版本，而没有仅沿用旧PASS。

## 候选与预览

沿用唯一候选 `SPIO_R008_Q200_N010_Candidate`，INP SHA-256为 `fa2de5d73a28536c1c07cd22072d2a24c1ae988c569127d728931c583457f05a`。路径、Job名和哈希均与run_008/run_010/run_012一致。用实际保存值构造只预览请求；资源/阶段/工作目录字段与run_012一致。

公开 `preflight` 返回 `PREVIEW_READY`，`enqueue(..., dry_run=True)` 返回 `DRY_RUN_READY`，命令预览与run_012一致。API报告没有启动Solver/Runner或修改Queue；Queue前后为空且哈希一致。Settings、Project manifest、live_status、候选INP及工作目录、用户recent/app_settings等保护文件均不变。没有调用Abaqus命令，没有执行datacheck、许可证签出、训练或原始模型编辑。

## 阻塞解除与AgentHub

run_012原结论保留为当时的BLOCKED；对其全部文件记录前后SHA-256，完全一致。新增 [阻塞解除记录](artifacts/run012_blocker_resolution.json)，将 `PROJECT_RUNTIME_SETTINGS_NOT_SAVED` 标记为 `RESOLVED_BY_NEW_EVIDENCE`，指向本Run的严格查询和预览证据。项目当前状态与Run索引引用这份新证据，未改写run_012历史文件或旧Hub任务结果。

在现有AgentHub SQLite中，以MAIN登记新审计任务 `e7d81ac3-0d08-4677-b4f4-f940fbda8209`，依赖run_012原任务。六项产物登记SHA-256和来源版本并回读校验；持久解除阻塞消息被MAIN收到，审计链有效。执行COMPLETED、证据RECORDED、科学状态NOT_EVALUATED。

主要证据：[严格Settings查询](artifacts/settings_api_response.json)、[综合核验](artifacts/verification_result.json)、[AgentHub回执](artifacts/agenthub_receipt.json)。本轮新增run_013脚本、记录及证据，更新Run索引和项目当前状态；未修改外部源码/环境，未commit/push。

## 授权范围

现在可申请对这一确切候选INP及哈希、此Project和已核实配置开展第一次单次受控正向求解。实际写入Queue与启动仍需明确授权；当前Run不包含这些动作。求解能力、许可证可用性和收敛需真实执行验证。本构仍为真总应变解释下的候选模型，未获得实验验证，历史源INP与当前已编辑CAE数据库的一致性仍UNKNOWN。第一次求解应按该候选INP开展工程验证，不能预先宣称物理模型有效。本Run到此停止。
