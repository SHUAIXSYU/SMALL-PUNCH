import unittest,sys,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
from inverse.fd_loss import Curve,Target,InvalidCurve
from compare_validation import compare

class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.grid=(0.,.0005,.001);self.curve=Curve(self.grid,(0.,50.,100.),'m','N')
        self.target=Target(self.curve,(1.,1.,1.),100.,'synthetic-v1')
        self.contract={'loss_version':'synthetic-v1','force_reference_n':100.,'point_count':3,'grid_m':list(self.grid),'relative_force_floor_n':5.,'thresholds':{'force_rmse_n':2.,'max_absolute_force_n':7.,'max_regularized_relative':.05,'absolute_loss_change':.001}}
    def runcompare(self,v,**kw):return compare(self.target,self.curve,v,self.contract,original_status='COMPLETED',validation_status=kw.get('status','COMPLETED'))
    def test_identical_zero(self):
        r=self.runcompare(self.curve);self.assertEqual(r['force_rmse_n'],0);self.assertEqual(r['status'],'CURVE_GATE_PASS')
    def test_different_sampling(self):
        r=self.runcompare(Curve((0.,.001),(0.,100.),'m','N'));self.assertEqual(r['force_rmse_n'],0)
    def test_constant_offset_known_metrics(self):
        r=self.runcompare(Curve(self.grid,(1.,51.,101.),'m','N'));self.assertAlmostEqual(r['force_rmse_n'],1);self.assertAlmostEqual(r['loss_change'],.0001);self.assertEqual(r['status'],'CURVE_GATE_FAIL');self.assertAlmostEqual(r['max_regularized_relative'],.2)
    def test_threshold_violation(self):
        r=self.runcompare(Curve(self.grid,(0.,54.,104.),'m','N'));self.assertFalse(r['checks']['force_rmse'])
    def test_no_extrapolation(self):
        with self.assertRaises(InvalidCurve):self.runcompare(Curve((.0001,.001),(10.,100.),'m','N'))
    def test_nan(self):
        with self.assertRaises(InvalidCurve):Curve(self.grid,(0.,float('nan'),100.),'m','N')
    def test_nonmonotonic(self):
        with self.assertRaises(InvalidCurve):Curve((0.,.001,.0005),(0.,100.,50.),'m','N')
    def test_units(self):
        with self.assertRaises(InvalidCurve):Curve(self.grid,(0.,50.,100.),'mm','N')
    def test_failed_fe(self):
        with self.assertRaises(InvalidCurve):self.runcompare(self.curve,status='FAILED')
    def test_zero_force_relative(self):
        r=self.runcompare(self.curve);self.assertEqual(r['raw_relative_excluded_count'],1);self.assertEqual(r['max_raw_relative_above_floor'],0)
    def test_changed_grid(self):
        self.contract['grid_m'][1]=.0004
        with self.assertRaises(ValueError):self.runcompare(self.curve)
    def test_changed_version_or_normalization(self):
        self.contract['loss_version']='other'
        with self.assertRaises(ValueError):self.runcompare(self.curve)
        self.contract['loss_version']='synthetic-v1';self.contract['force_reference_n']=99.
        with self.assertRaises(ValueError):self.runcompare(self.curve)
if __name__=='__main__':unittest.main(verbosity=2)
