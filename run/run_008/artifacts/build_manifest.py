import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
entries=[
('agenthub_sp_invopt/hub.py','SQLite role/task/message/approval/evidence ledger implementation'),
('agenthub_sp_invopt/poll.py','Bounded persistent inbox poller and transactional claim process'),
('agenthub_sp_invopt/README.md','Independent Hub overview and usage'),
('agenthub_sp_invopt/protocol.md','Task, message, lease, approval and evidence protocol'),
('agenthub_sp_invopt/STARTUP.md','MAIN, CAE and ODB startup and Handoff instructions'),
('agenthub_sp_invopt/abqjobpilot_project/project.json','AbqJobPilot formal Project identity'),
('run/run_008/artifacts/generate_candidate_inp.py','Candidate input generator'),
('run/run_008/artifacts/candidate_inp/SPIO_R008_Q200_N010_Candidate/SPIO_R008_Q200_N010_Candidate.inp','Unique candidate INP and isolated job directory; source lineage in ignored private audit'),
('run/run_008/artifacts/validate_candidate_inp.py','Abaqus input parser syntax validation script'),
('run/run_008/artifacts/candidate_inp_parse.json','Abaqus 2024 parser result; syntax only'),
('run/run_008/artifacts/read_historical_odb.py','Abaqus ODB read-only interface regression script'),
('run/run_008/artifacts/historical_odb_interface.json','Historical ODB read-only evidence; not a candidate solve'),
('run/run_008/artifacts/setup_abq_project.py','Project creation and public API identity/capability audit script'),
('run/run_008/artifacts/abqjobpilot_project.json','Project ID, v0.2.2 capabilities and empty Project Queue record'),
('run/run_008/artifacts/mcp_readonly_audit.py','MCP stdio read-only audit client'),
('run/run_008/artifacts/mcp_readonly_results.json','MCP tool discovery, status, history, outputs and unchanged queue evidence'),
('run/run_008/artifacts/simulate_handoff.py','MAIN/CAE/ODB local process collaboration simulation'),
('run/run_008/artifacts/end_to_end_simulation.json','Structured local task handoff, claims, evidence and authorization results'),
('run/run_008/artifacts/cae_claimed_verification.py','Claimed CAE task candidate validation worker'),
('run/run_008/artifacts/cae_candidate_verification.json','Candidate input verification result'),
('run/run_008/artifacts/cae_verification_handoff.json','CAE result and MAIN inbox receipt evidence'),
('run/run_008/artifacts/test_hub.py','Eight standard-library AgentHub tests'),
('run/run_008/artifacts/hub_tests_final.txt','Final Hub test log'),
('run/run_008/artifacts/test_candidate_contract.py','Three candidate/ODB/Abq boundary tests'),
('run/run_008/artifacts/candidate_tests_final.txt','Final candidate contract test log'),
('run/run_008/artifacts/hub_state.json','SQLite counts, states and append-only event-chain check'),
('run/run_008/artifacts/verify_hub_state.py','SQLite final audit script'),
('run/run_008/artifacts/finalize_run_evidence.py','Final scoped validation assembler'),
('run/run_008/artifacts/final_validation.json','Final scoped acceptance and limitations'),
('run/run_008/artifacts/build_manifest.py','Artifact manifest generator'),
('run/run_008/artifacts/capture_final_state.py','Final preservation and external-state capture script'),
('run/run_008/summary.md','Run summary'),
('run/run_008/checkpoints/initial_state.json','Git and input baseline'),
('run/README.md','Run index update'),
('status/PROJECT_STATUS.md','Project state update'),
('docs/Research_Architecture.md','Actual AbqJobPilot and AgentHub status update'),
('docs/Agent_File_Communication_Protocol.md','Run and independent Hub boundary update'),
('README.md','English project status update'),
('README.zh-CN.md','Chinese project status update'),
('.gitignore','Ignore isolated Hub runtime and Project runtime state')]
artifacts=[]
for rel,role in entries:
    p=(ROOT/rel).resolve()
    if not p.is_relative_to(ROOT) or not p.is_file(): raise SystemExit('MANIFEST_PATH_INVALID_OR_MISSING:'+rel)
    h=hashlib.sha256(p.read_bytes()).hexdigest()
    artifacts.append({'path':rel,'role':role,'sha256':h,'publicity':'public'})
manifest={'schema_version':'1.0','run_id':'run_008','generated_at':__import__('datetime').datetime.now().astimezone().isoformat(),'artifacts':artifacts,'private_audit':{'path':'run/run_008/artifacts/private/','gitignored':True,'contains':['source path/hash, use/provenance and processing record','environment and real Settings-file discovery','resolved failure diagnostics'],'source_hashes_disclosed':False},'persistent_local_state':{'path':'agenthub_sp_invopt/runtime/sp_invopt.sqlite3','gitignored':True,'integrity_evidence':'run/run_008/artifacts/hub_state.json'}}
(ROOT/'run'/'run_008'/'artifacts'/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'artifact_count':len(artifacts),'manifest':'run/run_008/artifacts/manifest.json'},ensure_ascii=False))
