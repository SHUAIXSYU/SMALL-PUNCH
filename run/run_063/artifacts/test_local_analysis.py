"""Independent numerical checks for SVD scaling and scenario interpretation."""
from analyze_coupling import *
import unittest,io
class Checks(unittest.TestCase):
 def test_known_diagonal(self):
  a=decomposition([[4.,0],[0,1.]])
  np.testing.assert_allclose(a['singular_values'],[4.,1.]);self.assertEqual(a['condition_number'],4.);self.assertEqual(a['rank'],2)
 def test_singular_is_not_evaluable(self):
  a=decomposition([[1.,2.],[2.,4.]])
  self.assertEqual(a['status'],'NOT_EVALUABLE');self.assertIsNone(a['condition_number'])
 def test_common_row_scale_preserves_condition(self):
  J=np.array([[1.,2.],[3.,1.],[.1,.3]])
  a=decomposition(J);b=decomposition(7*J)
  self.assertAlmostEqual(a['condition_number'],b['condition_number']);np.testing.assert_allclose(np.array(a['singular_values'])*7,b['singular_values'])
 def test_weak_mode_known_parameter_offset(self):
  J=np.array([[1.,1.],[.2,.5],[.3,.4]]);a=decomposition(J);v=np.array(a['weak_direction_xy']);z=J@(H*v);dq=np.linalg.pinv(J)@z
  np.testing.assert_allclose(dq,H*v,rtol=1e-13,atol=1e-14)
  self.assertAlmostEqual(np.linalg.norm(z),H*a['singular_values'][-1])
 def test_partition_RMS_scaling(self):
  d=read(P/'verified_local_data.json');x={k:np.array(v) for k,v in d['curves_N'].items()};raw=np.column_stack([(x['P02']-x['P01'])/.05,(x['P04']-x['P03'])/.05]);parts=read(P/'band_SVD_analysis.json')['bands'][:4];G=sum(b['points']*np.array(b['J']).T@np.array(b['J'])/241 for b in parts)
  np.testing.assert_allclose(G,(raw/FREF).T@(raw/FREF)/241,rtol=1e-13,atol=1e-14)
 def test_scenarios_RMS_and_symmetric_offsets(self):
  a=read(P/'analysis_arrays.json');amp=a['reference_amplitude_N'];rs=rows(P/'scenario_parameter_sensitivity.csv');selected=[r for r in rs if r['shape']=='aligned_weak_mode' and r['view']=='full241' and float(r['input_RMS_factor'])==1]
  self.assertEqual(len(selected),2);self.assertAlmostEqual(float(selected[0]['delta_x']),-float(selected[1]['delta_x']))
  for name,f in a['scenario_force_profiles'].items():
   multiplier=float(name.split('_RMSx')[1].split('_sign')[0]);self.assertAlmostEqual(float(np.sqrt(np.mean(np.array(f)**2))),amp*multiplier,places=12)
if __name__=='__main__':
 stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks));write(P/'unit_tests.log',stream.getvalue());save(P/'unit_tests.json',{'tests_run':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'success':r.wasSuccessful(),'scope':'analytic SVD/rank, RMS row scaling, deterministic offsets; no Solver or new fitted model'})
 print(stream.getvalue());sys.exit(0 if r.wasSuccessful() else 1)
