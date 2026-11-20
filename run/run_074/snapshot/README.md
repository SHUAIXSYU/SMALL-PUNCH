# run_074 — Stage 3 B2 verified FE snapshot

Eight actual B2 jobs completed with warnings, each one datacheck and one Full; 8/8 exploratory-scoreable. Actual execution Project `b9c0d50f-2655-4091-ae49-1bf08940acf8`, distinct from old b87 project. Inputs frozen in run070; job/queue identifiers and full INP/ODB hashes in jobs.csv. No new solver/datacheck/enqueue/retry in this analysis.

| 区间 | 负/正相对I06 RMS N | 负/正最大差 N | 配对RMS N | 奇/偶RMS N | 偶/奇 | 目标配对dQ MPa |
| --- | --- | --- | --- | --- | --- | --- |
| S1 | 9.018646 / 9.861842 | 15.530188 / 17.221234 | 18.878900 | 9.439450 / 0.439012 | 0.046508 | 11.934017812 |
| S2 | 4.035454 / 4.423235 | 6.808411 / 7.489624 | 8.449358 | 4.224679 / 0.277553 | 0.065698 | 3.634586686 |
| S3 | 3.074739 / 3.431583 | 6.210510 / 9.442704 | 6.404756 | 3.202378 / 0.599721 | 0.187274 | 0.000000000 |
| S4 | 0.586654 / 0.650639 | 1.804321 / 1.984436 | 1.234473 | 0.617236 / 0.052596 | 0.085211 | 0.000000000 |

Supports p=[0,.03],[.03,.098261747064013],[switch,.30],[.30,.60]; factors1/1.1 and1.1 with compact C2 hardening-rate multipliers. Stress offsets continue after support. Q is deployed-table uniaxial true stress vs true total strain, not tensile measurements. S3/S4 preserve Q through .1 but change measured FE F–D. This supports forward sensitivity, **not complete H2 inverse compatibility**. H1 prior directional separation supported locally; H3 unresolved; H4 not evaluated. Formal external material validation NOT_EVALUABLE; historical exposure remains documented.

Numerical quality WARNING, resolution LIMITED. Center adjacent-step difference .432677914N is an exploratory scale, not endpoint error bounds. All241points retained, including contact events. Pair finite secants are not formal derivatives or Fisher information. Segments [0:60],[60:120],[120:180],[180:241]. `K` units N per dimensionless log-rate multiplier. Correlation does not prove independent identification or actual compensation.

Data: fd_241.csv (FE only); sensitivity_241.csv (odd/even/K); target_981.csv (.002–.1,981points); jobs.csv (identity/status/warnings), metrics.json. Missing partner experiment and raw private evidence intentionally withheld; no experimental SPT or tensile curves/Loss/residuals published. FE standardization and target arrays are newly built reviewed research derivatives explicitly requested for public snapshot, not publication of raw private artifacts.

Reproduce response arithmetic with b2_metrics.py; `python test_b2_metrics.py` tests only synthetic fixtures and never treats them as FE. Workflow source code hash/version and dataset hashes are in snapshot_manifest.json. Figures use actual FE data and material tables; private residual and experiment-derived figures excluded.

Next: B4 12 comparison slots=4 existing zero controls +8 bounded compensation/reverse drafts; prioritize four S2 branch tests, no new inputs or execution authorization. Candidate-specific .1 strain connection required; only future real FE can confirm tau1/2/5/10N compatibility and Q range. B3≤4 conditional reserve retained. Actual Stage3 budget16/40, remaining24 planned, no automatic spending.

Additional actual diagnostics: figures09–12 and reference_volume_stages.csv. CAX4 reference volume uses 2πr detJ quadrature at integration points; saved-stage mismatch is retained. Bottom shapes are virtual FE outputs, no DIC measurement accuracy claim. Threshold-after-crossing plastic work decomposition not evaluated. Run reproduce.py to independently recalculate all published RMS response metrics from the released FE CSV.
