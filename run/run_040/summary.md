# run_040 — BO/DE 先导优化离线准备

**WARNING / READY_TO_REQUEST_FIRST_GATE_WITH_NUMERICAL_RISK。** run_039的19个可评分点及D07/D09/D10三个null记录已按身份与哈希冻结；算法测试5项通过。BO为一次性Kriging believer批量4点，DE为8个体种群的半代4个trial，均未使用新FE观测。真实CAE Agent完成8份独立INP，MAIN收到AgentHub消息并复核；8/8 Preflight、8/8 Dry-run通过。Queue未改变，0次新Datacheck/Solver/入队。

BO01、BO02、DE02靠近历史低n数值阻塞区，BO03紧邻σy下界；GP拟合超参数触及预设边界。可申请最多8次首关新高保真尝试，但须明确数值风险、失败照算预算、逐项审核与暂停条件；第二关4+4只能在首关结果后另行决定。本Run无计算授权，停止等待指令。

完整[私有研究报告](artifacts/private/MAIN_REPORT.md)、[算法及公平性协议](artifacts/pilot_protocol.md)、[工程复核](artifacts/private/main_cae_review.json)与[CAE证据](artifacts/private/cae/REPORT.md)。保留既往拉伸资料暴露声明，不解盲、不改原始模型、不commit/push。
