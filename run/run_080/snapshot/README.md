# run_080 — B3数值分辨与高低段响应补偿

**三个真实Job均完成，数值质量WARNING；原2N名义相容判定不稳健。** 每项DC一次+Full一次、零重试、1602原生点、0cutback；全部接受态力/接触收敛标志核验。14CPU/0GPU。Project b9c0d50f-2655-4091-ae49-1bf08940acf8。完整身份及INP/ODB SHA见jobs.csv。

| 候选 | 粗细RMSE N | 最大差 N @ mm | L1相对同层中心 RMS N | L2相对同层中心 RMS N | 相对残差跨层变化 RMS N |
| --- | --- | --- | --- | --- | --- |
| B4_01 | 0.198099401 | 1.246147707 @ 1.125 | 2.142391666 | 2.117338108 | 0.144735316 |
| B4_02 | 0.216060377 | 1.289867354 @ 0.980 | 1.934924147 | 2.028236039 | 0.239558630 |
| I06_REFINED | 0.198344900 | 1.255790458 @ 1.125 | 0（参考） | 0（参考） | — |

| 候选 | tau N | L1边距 N | L2边距 N | L1→L2内/外 | 风险筛查 |
| --- | --- | --- | --- | --- | --- |
| B4_01 | 1.0 | -1.142391666 | -1.117338108 | False → False | NO_FLAG_FROM_THIS_OBSERVED_TWO_LEVEL_SCREEN |
| B4_01 | 2.0 | -0.142391666 | -0.117338108 | False → False | UNRESOLVED |
| B4_01 | 5.0 | +2.857608334 | +2.882661892 | True → True | NO_FLAG_FROM_THIS_OBSERVED_TWO_LEVEL_SCREEN |
| B4_01 | 10.0 | +7.857608334 | +7.882661892 | True → True | NO_FLAG_FROM_THIS_OBSERVED_TWO_LEVEL_SCREEN |
| B4_02 | 1.0 | -0.934924147 | -1.028236039 | False → False | NO_FLAG_FROM_THIS_OBSERVED_TWO_LEVEL_SCREEN |
| B4_02 | 2.0 | +0.065075853 | -0.028236039 | True → False | UNRESOLVED |
| B4_02 | 5.0 | +3.065075853 | +2.971763961 | True → True | NO_FLAG_FROM_THIS_OBSERVED_TWO_LEVEL_SCREEN |
| B4_02 | 10.0 | +8.065075853 | +7.971763961 | True → True | NO_FLAG_FROM_THIS_OBSERVED_TWO_LEVEL_SCREEN |

L2 B4_01/B4_02均在tau2外，B4_02从内翻为外。残差跨层变化约.145/.240N，大于新tau2边距.117/.028N，预注册筛查均UNRESOLVED。不能用一次减半证明严格时间或网格收敛，不删去接触尖峰。tau为确定性RMS场景，不是仪器误差/置信界。

两个补偿目标dQ=3.634586685959MPa，实际材料与低段Q新旧逐字节继承，目标曲线不变。L2 tau1/2三点池只有中心，tau5/10含三点；尚无细层S2零对照，完整固定/自由高段族NOT_EVALUABLE。单点集合不是唯一性证明，有限FE池不是全域不确定性上界。

H1保持局部SUPPORTED；H2-A真实响应补偿SUPPORTED，H2-B稳健目标范围扩大UNRESOLVED；H3/H4未分辨，正式真实材料独立验证NOT_EVALUABLE。原run077对抵消/增强的事实不重写。历史信息暴露声明保持，本轮未读取/使用拉伸真值。

真实已有ODB场诊断：10个已有模型四阶段S/PEEQ/U/接触可用；2pi*r*detJ参考体积权重。细层终态PEEQ>.1约12.25–12.31%体积，>.3约6.14–6.20%，>.5约1.77%；最大PEEQ<.9。应力按参考位置分组，当前Cauchy近表面IP均值/差只作弯曲/膜作用线索，不声称严格转变点或区域反力贡献。区域塑性耗散字段缺失，NOT_EVALUABLE；全局ALLPD保留。场、接触和虚拟形状机制报告及图件补充于mechanisms.md。

推荐现在不追加FE：先用已有ODB与形状数值信号分析，不机械消耗B3第四项。如果要求完整双侧同层控制，需另授权S2±两项，B3总5超过上限4，须显式重分配；这本身不能补成2N稳健扩大证据。Stage3实际23/40、余17条件规划，Agent本轮新Solver/DC/Queue=0。

数据：fd_levels_241.csv为线性插值标准0..1.2mm/241点（u=-U2,F=-RF2，m转mm，无2pi、平滑、零移或外推）；target_Q_981.csv为实际塑性表epsilon=p+sigma/E加弹性原点转换的.002.. .1真总应变MPa；field_stage_summary.csv为真实保存阶段PEEQ参考体积分数，保留u偏差。全部为明确获准的纯FE派生研究数据，无合作方实验曲线、原始INP/ODB/CAE、private完整报告或数据库。

运行`python reproduce.py`从公开CSV重新计算冻结规则的范数/容差/目标直径。这是算术复现，不是新的FE、独立验证或统计置信证明。来源版本、逐文件SHA及发布审查见snapshot_manifest.json。科研状态WARNING，Git发布不改变科学结论。
