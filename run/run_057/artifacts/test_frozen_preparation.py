"""Read-only candidate, frozen inference and synthetic A/B metric checks."""
from common import *
import unittest, csv
import numpy as np
sys.path[:0]=[str(P/'frozen_predictor/code'),str(A)]
from feature_core import extract
from inverse_baselines import predict_model, support
from predict_frozen import predict_file
from prospective_metrics import local_secants,recovery_score

class PreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c=read(P/'candidate_generation.json');cls.b=read(R/'run/run_056/artifacts/private/prospective_design_contract.json');cls.pack=P/'frozen_predictor';cls.models=read(cls.pack/'frozen_FE_only_inverse_models.json')

    def test_all_input_hashes_and_skeleton(self):
        source=(R/self.b['baseline']['inp_path']).read_bytes()
        for p in self.c['points']:
            self.assertEqual(sha(R/p['inp_path']),p['inp_sha256'])
            self.assertEqual(effective_skeleton((R/p['inp_path']).read_bytes()),effective_skeleton(source))

    def test_numeric_or_BC_tamper_is_detected(self):
        raw=(R/self.c['points'][0]['inp_path']).read_bytes()
        changed=raw.replace(b'0.001, 1., 1e-12, 0.0025',b'0.001, 1., 1e-12, 0.00125')
        self.assertNotEqual(effective_skeleton(raw),effective_skeleton(changed))
        self.assertNotEqual(hashlib.sha256(raw).hexdigest(),hashlib.sha256(changed).hexdigest())

    def test_material_monotonic_units_and_coverage(self):
        for p in self.c['points']:
            _,_,v=split_plastic((R/p['inp_path']).read_bytes());v=np.array(v)
            self.assertEqual(v[0,0],p['sigma_y_mpa']*1e6);self.assertEqual(v[0,1],0);self.assertEqual(v[-1,1],.9)
            self.assertTrue(np.all(np.diff(v,axis=0)>0));self.assertLessEqual(p['dense_15000_check_max_relative_error'],.001)

    def test_previews_and_no_writes(self):
        evidence=read(P/'preflight_dry_run_results.json')
        self.assertEqual(evidence['preflight_passed'],4);self.assertEqual(evidence['dry_run_passed'],4)
        self.assertEqual(evidence['protected_before'],evidence['protected_after']);self.assertTrue(evidence['queue_unchanged'])
        for p in self.c['points']:self.assertFalse(any((R/p['working_dir']).iterdir()))

    def test_no_extrapolation_or_invalid_FD(self):
        with self.assertRaises(ValueError):extract([0,.001],[0,1])
        with self.assertRaises(ValueError):extract([0,.0012,.001],[0,1,2])
        with self.assertRaises(ValueError):extract([0,.0012],[0,float('nan')])

    def test_packaged_inference_matches_original(self):
        before=sha(self.pack/'frozen_FE_only_inverse_models.json')
        output=predict_file(self.pack,R/self.b['baseline']['fd_path'])
        a=read(R/'run/run_055/artifacts/private/feature_arrays.json')
        from feature_core import normalized_to_physical
        for name in ['two_ridge','five_ridge','full_ridge']:
            v=self.models['models'][name];q=a['curves']['I06'] if v['input']=='full' else a['features']['I06']
            expected=normalized_to_physical(predict_model(v['model'],q))[0]
            actual=output['predictions'][name]
            np.testing.assert_array_equal(expected,[actual['sigma_y_mpa'],actual['n']])
        self.assertEqual(before,sha(self.pack/'frozen_FE_only_inverse_models.json'))
        self.assertTrue(output['no_training_or_tuning'])

    def test_training_exactly25_not250(self):
        train=read(self.pack/'training_25.json');self.assertEqual(len(train['sample_ids']),25)
        self.assertEqual(len(set(map(tuple,train['targets_MPa_n']))),25)
        self.assertFalse({'H01','H02','D07','D09','D10','BO01','BO02','DE02'}&set(train['sample_ids']))
        self.assertEqual(sha(self.pack/'frozen_FE_only_inverse_models.json'),self.b['frozen_models']['frozen_inverse_models_sha256'])

    def test_synthetic_secants_recover_known_scaled_map(self):
        center=np.array([10.,20.,30.]);sx=np.array([1.,2.,0.]);sy=np.array([0.,1.,2.]);h=.025
        r=local_secants(center,center-h*sx,center+h*sx,center-h*sy,center+h*sy,np.ones(3))
        np.testing.assert_allclose(r['J'],np.column_stack([sx,sy])/np.sqrt(3),atol=1e-12)
        self.assertEqual(r['rank'],2);self.assertLess(r['axes']['x']['even_odd_ratio'],1e-10)
        self.assertEqual(r['step_convergence'],'NOT_EVALUABLE')

    def test_rank_deficiency_not_claimed_identifiable(self):
        c=np.array([1.,2.]);s=np.array([3.,4.]);h=.025
        r=local_secants(c,c-h*s,c+h*s,c-2*h*s,c+2*h*s,np.ones(2))
        self.assertEqual(r['rank'],1);self.assertIsNone(r['condition_number']);self.assertEqual(r['Fisher_CI'],'NOT_EVALUABLE')

    def test_constant_center_fails_resolution_goal(self):
        truth=np.array([[p['sigma_y_mpa'],p['n']] for p in self.c['points']]);center=np.tile([self.b['baseline']['sigma_y_mpa'],self.b['baseline']['n']],(4,1))
        result=recovery_score(center,truth)
        self.assertAlmostEqual(result['E_local'],2**-.5)
        self.assertFalse(result['engineering_resolution_goal_met']);self.assertFalse(result['beats_constant_I06'])
        self.assertFalse(any(result['active_axis_sign_correct']))
        exact=recovery_score(truth,truth);self.assertTrue(exact['engineering_resolution_goal_met']);self.assertEqual(exact['E_local'],0)

    def test_local_CAEs_and_staging_preserved(self):
        start=read(RUN/'checkpoints/start.json')
        self.assertEqual(git('diff','--cached','--name-status'),start['staged'])
        self.assertEqual(sha(R/'.gitignore'),start['gitignore_sha256'])
        for m in start['local_CAE']:self.assertEqual(sha(R/m['path']),m['sha256'])

if __name__=='__main__':unittest.main()
