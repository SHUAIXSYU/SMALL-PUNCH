"""Synthetic checks of comparison bookkeeping; no FE or experimental data."""
import sys, unittest
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(R));sys.path.insert(0,str(Path(__file__).parent))
from inverse.fd_loss import Curve,Target
from sensitivity_metrics import assess_curve,pair_symmetry

class MetricsTests(unittest.TestCase):
 def setUp(self):
  self.u=tuple(i*0.0012/240 for i in range(241))
  self.f=tuple(1000*u/.0012 for u in self.u)
  self.t=Target(Curve(self.u,self.f,'m','N'),(1.,)*241,1428.9,'synthetic-only')
 def assess(self,force,accepted=True):
  return assess_curve(self.t,Curve(self.u,tuple(force),'m','N'),np.array(self.f),software_status='COMPLETED_WITH_WARNINGS',numerical_accepted=accepted)[0]
 def test_identity(self):
  m=self.assess(self.f);self.assertEqual(m['loss'],0);self.assertEqual(m['RMSE_vs_D01_N'],0)
 def test_known_offset_and_partition(self):
  m=self.assess(np.array(self.f)+2)
  self.assertAlmostEqual(m['loss'],(2/1428.9)**2)
  self.assertAlmostEqual(m['RMSE_vs_D01_N'],2)
  self.assertEqual([b['points'] for b in m['bands']],[60,60,60,61])
  self.assertAlmostEqual(sum(b['loss_contribution_full_window'] for b in m['bands']),m['loss'])
 def test_rejected_quality_has_null_loss(self):
  m=self.assess(self.f,False);self.assertIsNone(m['loss']);self.assertIsNone(m['RMSE_to_experiment_N'])
 def test_opposing_symmetry(self):
  a=np.array(self.f);m=pair_symmetry(a-5,a+5,a)
  self.assertAlmostEqual(m['relative_antisymmetry_defect'],0,places=14)
  self.assertAlmostEqual(m['midpoint_response_RMSE_vs_D01_N'],0,places=12)
 def test_no_perturbation_not_defined(self):
  m=pair_symmetry(self.f,self.f,self.f);self.assertIsNone(m['relative_antisymmetry_defect'])

if __name__=='__main__':unittest.main(verbosity=2)
