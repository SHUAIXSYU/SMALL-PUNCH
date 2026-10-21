import hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; JOB='SPIO_R008_Q200_N010_Candidate'
INP=ROOT/'run'/'run_008'/'artifacts'/'candidate_inp'/JOB/(JOB+'.inp')
class CandidateContract(unittest.TestCase):
    def test_unique_candidate_material_and_provenance(self):
        data=INP.read_text(encoding='utf-8'); lines=data.splitlines()
        self.assertEqual(INP.stem,JOB); self.assertEqual(INP.parent.name,JOB)
        self.assertEqual(data.count('CANDIDATE ONLY: candidate-true-total-hollomon-v1'),1)
        self.assertIn('True total Hollomon; p = epsilon_total - sigma/E',data)
        a=lines.index('*Elastic'); self.assertEqual(lines[a+1].strip(),'2.1e+11, 0.3')
        p=lines.index('*Plastic'); rows=[]
        for line in lines[p+1:]:
            if line.lstrip().startswith('*'): break
            if line.strip() and not line.lstrip().startswith('**'):
                nums=[float(x.strip()) for x in line.split(',')]; rows.append(nums)
        self.assertEqual(len(rows),35); self.assertEqual(rows[0],[200000000.0,0.0]); self.assertAlmostEqual(rows[-1][1],0.9)
        audit=json.loads((ROOT/'run'/'run_008'/'artifacts'/'private'/'candidate_source_audit.json').read_text(encoding='utf-8'))
        self.assertEqual(hashlib.sha256(INP.read_bytes()).hexdigest(),audit['output_sha256'])
        self.assertEqual(hashlib.sha256((ROOT/audit['source_relative_path']).read_bytes()).hexdigest(),audit['source_sha256'])
    def test_historical_odb_is_interface_only_and_unchanged(self):
        result=json.loads((ROOT/'run'/'run_008'/'artifacts'/'historical_odb_interface.json').read_text(encoding='utf-8'))
        self.assertEqual(result['status'],'PASS_INTERFACE_ONLY'); self.assertEqual(result['candidate_material_solve'],'NOT_PERFORMED')
        self.assertEqual(result['source_sha256_before'],result['source_sha256_after'])
        self.assertEqual(result['outputs']['U2']['samples'],181); self.assertEqual(result['outputs']['RF2']['samples'],181)
    def test_abq_project_queue_and_run_boundary(self):
        result=json.loads((ROOT/'run'/'run_008'/'artifacts'/'mcp_readonly_results.json').read_text(encoding='utf-8'))
        self.assertEqual(result['server_version']['version'],'0.2.2'); self.assertTrue(result['queue_unchanged'])
        self.assertEqual(result['calls']['abq_list_jobs:queue']['structured_content']['data']['jobs'],[])
        self.assertEqual(result['calls']['abq_list_jobs:history']['structured_content']['data']['jobs'],[])
        self.assertEqual(result['settings_dependent_tools']['abq_preflight'],'NOT_INVOKED_SETTINGS_UNKNOWN')
        parsed=json.loads((ROOT/'run'/'run_008'/'artifacts'/'candidate_inp_parse.json').read_text(encoding='utf-8'))
        self.assertEqual(parsed['status'],'PASS_ABAQUS_INPUT_PARSE')

if __name__=='__main__': unittest.main(verbosity=2)
