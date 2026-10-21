# run_014 ODB Agent result

**Execution:** AbqJobPilot records the one authorised full analysis as `COMPLETED_WITH_WARNINGS`, return code 0, after a passing datacheck. **Extraction:** PASS for the specified ODB, Punch RP history and model-unit curve. **Science:** `NOT_EVALUATED`; this is a forward model result, not an experimental fit or physical validation.

## Identity and safe read

- Hub task `35b07ba1-22ad-48a7-b859-2d99199ed419`; ODB session `2d884cb1-8cc4-483f-b703-3215c897c369`; Project `b87d2cd6-8519-4ac3-bae6-7eb989fb2dae`; queue `q_4c0358a918a7447d807d2f547d22c7b8`; Job `SPIO_R014_Q200_N010`.
- Candidate INP SHA-256 `fa2de5d73a28536c1c07cd22072d2a24c1ae988c569127d728931c583457f05a`; new ODB SHA-256 `1ed3ecb6b2e3e2bfcfc806eb7edfab706b4acc90ec387ac641a81f529d9dd4fd`. Both matched the task and terminal evidence. ODB hash was unchanged before and after read-only extraction.
- Independent public `AbqJobPilotClient.status` and `locate_outputs` calls matched this queue, INP and recorded ODB path. Queue had exactly one matching record. `.lck` was absent, ODB size/mtime/hash were stable over two reads, and a current scan found no relevant Abaqus solver process. The prior Runner's Full-process aggregate remains **UNCONFIRMED** for transient PID 14320; the independent read-safety observations do not erase that historical gap. Details: [preflight_read.json](preflight_read.json) and [solver terminal evidence](../solver_terminal_result.json).
- Abaqus 2024 Python 3.10.5 opened the file with `odbAccess.openOdb(readOnly=True)`, reported `isReadOnly=True`, no required upgrade, and `JOB_STATUS_COMPLETED_SUCCESSFULLY` with 0 analysis errors and 6 ODB diagnostic warnings. MSG/STA/LOG also record successful completion. ODB validity is established only for the stated extraction scope.

## Punch force–displacement

The candidate INP associates `ASM_SPT.set_punch_rp` with the rigid-body reference node. The ODB has `Node ASM_SPT.1`; U2 and RF2 history data share an identical time array. RP field U2/RF2 equals history at all 170 saved frames (maximum absolute differences 0). The 169 accepted increments reach model step time 1.0.

| Quantity | New run_014 | Historical run_005 Sanity |
| --- | ---: | ---: |
| Saved F–D points | 170 | 181 |
| Final raw U2 (model length) | −0.001200000057 | −0.001200000057 |
| Final raw RF2 (model force) | −755.8150635 | −755.8928833 |
| Final / saved peak positive force | 755.8150635 | 755.8928833 |
| Final force difference, new minus historical | −0.0778198 | — |

Downward-positive displacement is `d = −U2`; applied positive compressive force is `F = −RF2`. Raw signed histories are preserved in [punch_history_raw.csv](punch_history_raw.csv); transformed values in [punch_force_displacement.csv](punch_force_displacement.csv). No absolute value, baseline shift, smoothing or `2π` factor was applied. Physical length, force and time units remain unverified, so all axes use model units.

The historical reference is the actual Sanity Job-1 model CSV, SHA-256 `42acf8ccf72a86a178a55ea3b27917367385cd4a730c20741d19bc87528f6670`, associated with historical ODB SHA-256 `612bdc14d02642bf66982a4cb00f8c85a08c98b069fb230f5d430cb8709b3d8f`. Linear interpolation of historical force onto each new displacement gives maximum absolute model force difference **13.5922** at displacement **0.000160815**, and RMS difference **6.13379** over the 170 new points. These are descriptive differences between *two model runs*. The near-identical endpoint does not mean the curves coincide. See [comparison CSV](historical_comparison.csv) and [plot](force_displacement_comparison.png). No experimental Loss was calculated.

## Numerical diagnostics

- Integration-point field `PEEQ` is available at every saved frame, with 2,376 values at the final frame. Its maximum over saved frames and final frame is **0.6938983**, below the candidate material table's `pmax=0.9` by **0.2061017**. This is stored-frame coverage, not a guarantee for unsaved trial states or future parameters. See [PEEQ CSV](peeq_saved_frames.csv).
- STA contains **169 accepted increments and 39 rejected attempts**; MSG final summary reports 39 automatic cutbacks. MSG has 35 analysis warning headers, including 4 negative-eigenvalue headers, 2 excessive-distortion headers, 25 large-strain-increment headers and 2 plasticity-not-attempted headers. The negative-eigenvalue and excessive-distortion headers occur in rejected trial attempts at increments 1, 96 and 147; they remain a numerical sensitivity warning. The AbqJobPilot aggregate warning count is 38, and ODB diagnostic warning count is 6; these are different sources/counting scopes. Full context is in [warning_events.json](warning_events.json) and [diagnostics.json](diagnostics.json).
- Final model energies include `ALLIE≈0.538313`, `ALLPD≈0.536000`, `ALLSE≈0.00231243`, `ALLFD≈0.00895848`, `ALLWK≈0.549081`, `ALLAE=ALLSD=0`, `ETOTAL≈−5.82212e−5`. Trapezoidal `∫F dd≈0.549081503` differs from `ALLWK` by `5.83e−8` model energy units. Contact-specific terms are unavailable, so a full independent energy balance is **NOT VERIFIED**. See [energy CSV](energy_history.csv).

An initial read-only export failed because the Abaqus `Repository` object does not implement `.get()`; its failure JSON is retained in the ignored private subdirectory. The corrected second attempt passed without altering the ODB. No Solver, datacheck, retry, queue write, model edit, dependency install, or experimental Loss was performed by this Agent.
