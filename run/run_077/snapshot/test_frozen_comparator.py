"""Synthetic fixtures test the frozen future comparison arithmetic, not FE evidence."""
import unittest,numpy as np
from frozen_comparator import *
class Tests(unittest.TestCase):
 def setUp(self):self.g=np.linspace(0,1.2,241);self.c=np.ones(241)*100
 def test_complete_gate(self):
  with self.assertRaises(ValueError):evaluate(self.c,{}, {},{}, {},self.g)
 def test_pairs_and_competence(self):
  z={'B2_S2_P':self.c+4,'B2_S2_M':self.c-4};d={'B4_01':self.c+1.5,'B4_02':self.c-1.5,'B4_03':self.c+7,'B4_04':self.c-7};q={'I06_REFINED':np.zeros(981),'B2_S2_P':np.ones(981),'B2_S2_M':-np.ones(981),**{k:np.ones(981)*(1 if k in ['B4_01','B4_03'] else -1) for k in d}};v=evaluate(self.c,z,d,d,q,self.g)
  self.assertAlmostEqual(v['pairs']['opposed']['odd']['RMS_N'],1.5);self.assertAlmostEqual(v['pairs']['opposed']['even']['RMS_N'],0);self.assertEqual(v['compatibility'][1]['fixed']['state'],'SINGLETON');self.assertAlmostEqual(v['compatibility'][1]['finite_diameter_increase_MPa'],2);self.assertAlmostEqual(v['compatibility'][2]['finite_diameter_increase_MPa'],0)
 def test_segments(self):self.assertEqual([j for a,b in SEGMENTS for j in range(a,b)],list(range(241)))
if __name__=='__main__':unittest.main()
