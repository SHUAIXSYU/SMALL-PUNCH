# run_033 — 20 Job DOE batch queue-only

**WARNING / TWENTY_JOBS_QUEUED_AWAITING_MANUAL_START。** 用户明确授权20个新增Job和GUI中一次Start Queue；Codex只通过AbqJobPilot 0.2.2公开API逐条queue-only入队，未启动Datacheck或Solver。正式Project ID `b87d2cd6-8519-4ac3-bae6-7eb989fb2dae`，PERSISTED Settings为Abaqus 2024、14 CPU/0 GPU、Datacheck+Full。最终公开接口回读恰好20项可执行记录，顺序、路径、SHA-256和资源与冻结清单一致，全部为QUEUED且独立工作目录为空；Runner空闲，无待恢复状态。I01/I02已完成，不在本批，未重复运行。

I02在入队前核查：唯一真实Queue/History执行尝试，Datacheck和Full日志返回0，Queue为`COMPLETED_WITH_WARNINGS`，STA完成，ODB/STA/MSG/DAT/LOG身份及哈希稳定，当前无锁或目标进程；数值警告保留待整批ODB分析，不把Solver完成当作科学有效。无阻塞性执行身份或文件冲突。

DOE设计在新INP生成前冻结：14新点中7个全域Latin hypercube、7个既有SPT低Loss邻域及宽裕边界的Sobol贪心最远点；固定种子、间距及归一化参数公式见`artifacts/doe_design.json`。低Loss依据是历史run_022的SPT-only PROVISIONAL证据，并非封存拉伸结果或真实材料答案。真实CAE会话通过AgentHub任务完成14份输入，MAIN独立核对20份材料表、非材料模型字节、数值设置、SHA-256与空输出目录。20/20公开Preflight、20/20 Dry-run通过，预览阶段Queue不变；冻结清单见`artifacts/prepared_batch.json`。

## 队列顺序

| 点 | Job | queue_id | sigma_y (MPa) | n |
| --- | --- | --- | ---: | ---: |
| I03 | `SPIO_R030_I03_G` | `q_4ffe11b3abd8448d9db5846afac395af` | 305.532235 | 0.200000 |
| I04 | `SPIO_R030_I04_L` | `q_67a8adc2beda42dfbca8838c18c47e3d` | 211.054605 | 0.173600 |
| I05 | `SPIO_R030_I05_G` | `q_381ef30aa78d4d099adcf0d6e07914de` | 490.946561 | 0.320000 |
| I06 | `SPIO_R030_I06_L` | `q_e60f5c549a89494ba59130fb0ae09bf1` | 236.499026 | 0.096800 |
| I07 | `SPIO_R030_I07_G` | `q_001628404e73449ba312596a79803967` | 788.880838 | 0.080000 |
| I08 | `SPIO_R030_I08_L` | `q_61465fe341104345ae82b5d93ee58ef2` | 265.010988 | 0.154400 |
| D01 | `SPIO_R033_D01_G` | `q_f26ab196938b49c2bc9af4784854e459` | 152.308634 | 0.230662 |
| D08 | `SPIO_R033_D08_L` | `q_4f19de5667ae4375b380aaf3d37adf5b` | 350.499769 | 0.123540 |
| D02 | `SPIO_R033_D02_G` | `q_a941177243aa46ab9e722b3e4514e114` | 305.180095 | 0.461299 |
| D09 | `SPIO_R033_D09_L` | `q_0bebaa417158409fba973efcbae921fd` | 157.388260 | 0.029674 |
| D03 | `SPIO_R033_D03_G` | `q_50674b73de494f218a519553098efc9d` | 665.124158 | 0.103335 |
| D10 | `SPIO_R033_D10_L` | `q_daff3a3f810f4c6b9622be278edb4942` | 263.796347 | 0.029641 |
| D04 | `SPIO_R033_D04_G` | `q_0f46b03533ab449482bcc602d83a7a62` | 207.296481 | 0.341678 |
| D11 | `SPIO_R033_D11_L` | `q_0e892571268d4b749d1b87477ab39f81` | 156.474255 | 0.164097 |
| D05 | `SPIO_R033_D05_G` | `q_9901c2ac7c07494cb0cdd9ebcd0f6347` | 817.023544 | 0.430998 |
| D12 | `SPIO_R033_D12_L` | `q_efbc2acf8a5f47198fa3c44caff50fa6` | 242.616511 | 0.230549 |
| D06 | `SPIO_R033_D06_G` | `q_1e05c9b46c0c4acdacd95946c127714b` | 463.519300 | 0.177183 |
| D13 | `SPIO_R033_D13_L` | `q_6a0932e3dc6e4721b5355fe94b071af6` | 297.354237 | 0.081706 |
| D07 | `SPIO_R033_D07_G` | `q_b4e48f5623bb442085bf92e63da64b3d` | 353.767221 | 0.042916 |
| D14 | `SPIO_R033_D14_L` | `q_ff61d70527e34b96b2848028cbf457d1` | 191.762866 | 0.230255 |

本批授权身份见`artifacts/authorization_scope.json`，20份完整INP路径、参数精度、完整SHA-256和工作目录见`artifacts/prepared_batch.json`，逐项公开API回执见`artifacts/queue_receipts/`，最终Queue证据见`artifacts/queue_manifest.json`。AgentHub记录20个独立队列任务、批准动作、queue_id和证据；审计链核验通过。20个Job尚未开始，预算已入队20/20、实际新增求解尝试0/20。运行后失败尝试同样消耗对应额度，零自动重试，不补点。

**AUTO_STOP_UNAVAILABLE。** GUI Start Queue可能串行运行全部20项，单个Job失败或严重警告不会可靠地自动停整个队列；用户已明确接受这一批量模式。请在正确Project确认队列只有上述20项后，亲自点击一次Start Queue。此动作尚未发生，Codex不会代点。整批实际终态由后续公开Queue/History核验，再交真实ODB会话只读批量提取；失败或不可信Job的Loss=null。当前未执行BO、DE或RL，未访问封存拉伸验证数据，保留历史信息暴露和旧Run结论，未commit/push。
