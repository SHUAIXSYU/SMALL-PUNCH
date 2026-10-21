# run_012 — Project Settings verification and API preview

**BLOCKED。** 目标Project的 `runtime/settings.json` 实际仍不存在，无法完成“从该Project Runtime读取已保存Settings”的验收。用户本条指令明确提供了命令和参数，因此本轮按这些明确值实际执行了官方API预览，没有用源码默认值代替未知配置。公开 `preflight` 返回 `PREVIEW_READY`；`enqueue(..., dry_run=True)` 返回 `DRY_RUN_READY`。两项预览通过不消除配置持久化阻塞。

## 核验结果

- Project ID `b87d2cd6-8519-4ac3-bae6-7eb989fb2dae`、正式根目录和实际runtime路径经公开API一致核验。
- 候选INP为run_008的独立 `SPIO_R008_Q200_N010_Candidate.inp`，SHA-256为 `fa2de5d73a28536c1c07cd22072d2a24c1ae988c569127d728931c583457f05a`，与任务/历史记录一致。
- Abaqus命令文件 `D:\ABAQUS2024\Commands\abq2024.bat` 确实存在并记录哈希；仅核验文件，没有调用该命令。
- 预览参数来源明确标为 `EXPLICIT_USER_MESSAGE_ONLY`：CPU14、GPU0、datacheck=true、full=true；用户声明自动关机关闭。不存在可读取的Project Settings，因此未把这些值声明为已持久化核实。源码预览命令与用户提供的命令路径一致。
- 稳定版AbqJobPilot0.2.2，公开API `preflight` 与 `enqueue(dry_run=True)` 均实际执行。没有调用Runner或非dry-run分支。
- Queue前后为空且哈希一致；Project manifest、live_status、Settings存在性、候选文件和目录、用户recent与app_settings均保持。没有新求解输出，未启动Solver/datacheck/自动关机或写入Queue。

## AgentHub与交付

在现有SQLite上以MAIN身份创建自身审计任务 `7d56b96f-bae2-473e-b9f6-89afb6dbcd14`，依赖run_010已完成的真实CAE核验任务。5项证据登记SHA-256，执行状态COMPLETED、证据RECORDED、科学状态NOT_EVALUATED；任务结果的检查状态明确为BLOCKED，不能把审计完成当成通过。持久结果消息及MAIN收件凭证已回读，审计链有效。没有模拟CAE或再次分派跨会话任务。

证据见 [配置核验](artifacts/settings_verification.json)、[preflight](artifacts/preflight.json)、[dry-run](artifacts/dry_run.json)、[综合结果](artifacts/preview_result.json) 和 [AgentHub回执](artifacts/agenthub_receipt.json)。本轮新增协调审计代码和证据，更新Run索引和项目状态；未改原始模型/稳定版源码/环境，未训练、commit或push。

仍不具备申请单次Solver授权的完整条件：先在该Project主窗口的Settings中实际保存，确保目标 `agenthub_sp_invopt/abqjobpilot_project/runtime/settings.json` 存在，再核对保存值与本轮预览一致。当前没有判断用户在GUI中未进行操作，只记录目标路径文件缺失这一可观察事实。实际入队和启动仍需明确授权；本构仍是候选真总应变解释，没有实验验证。本Run完成后停止。
