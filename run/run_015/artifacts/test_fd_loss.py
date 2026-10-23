"""Synthetic-only regression tests; no partner data or solver imports."""
import unittest
from dataclasses import replace
from inverse.fd_loss import Curve, Target, ScientificEvidence, InvalidCurve, ScientificGateError, evaluate


class LossTests(unittest.TestCase):
    def setUp(self):
        self.curve = Curve((0, .5, 1), (0, 1, 2), 'm', 'N')
        self.target = Target(self.curve, (1, 1, 1), 2, 'synthetic-v1')
        self.evidence = ScientificEvidence(True, True, True, True, True)

    def score(self, fe=None, **kwargs):
        args = {'fe_status': 'COMPLETED', 'evidence': self.evidence}
        args.update(kwargs)
        return evaluate(self.target, fe or self.curve, **args)

    def test_identical_zero(self):
        self.assertEqual(self.score()['loss'], 0)

    def test_different_sampling(self):
        self.assertEqual(self.score(Curve((0, 1), (0, 2), 'm', 'N'))['loss'], 0)

    def test_known_weighted_residual(self):
        target = replace(self.target, weights=(1, 2, 1))
        fe = Curve((0, .5, 1), (2, 3, 4), 'm', 'N')
        self.assertEqual(evaluate(target, fe, fe_status='COMPLETED', evidence=self.evidence)['loss'], 1)

    def test_no_overlap(self):
        with self.assertRaises(InvalidCurve):
            self.score(Curve((2, 3), (0, 1), 'm', 'N'))

    def test_partial_coverage_rejected(self):
        with self.assertRaises(InvalidCurve):
            self.score(Curve((0, .8), (0, 1.6), 'm', 'N'))

    def test_nan_and_infinity(self):
        for bad in (float('nan'), float('inf')):
            for u, f in (((0, bad), (0, 1)), ((0, 1), (0, bad))):
                with self.assertRaises(InvalidCurve): Curve(u, f, 'm', 'N')

    def test_nonmonotonic_and_duplicate(self):
        for u in ((0, 1, .5), (0, 0, 1)):
            with self.assertRaises(InvalidCurve): Curve(u, (0, 1, 2), 'm', 'N')

    def test_illegal_units(self):
        for units in (('mm', 'N'), ('m', 'kN'), ('m', 'unknown')):
            with self.assertRaises(InvalidCurve): Curve((0, 1), (0, 1), *units)

    def test_invalid_failed_fe(self):
        for state in ('FAILED', 'RUNNING', 'QUEUED', None):
            with self.assertRaises(InvalidCurve): self.score(fe_status=state)

    def test_gate_and_explicit_provisional(self):
        with self.assertRaises(ScientificGateError): self.score(evidence=ScientificEvidence())
        result = self.score(evidence=ScientificEvidence(), mode='PROVISIONAL')
        self.assertEqual(result['mode'], 'PROVISIONAL')
        self.assertEqual(len(result['unresolved']), 5)

    def test_bad_target(self):
        for w, ref in (((0, 0, 0), 2), ((1, -1, 1), 2), ((1, 1), 2), ((1, 1, 1), 0)):
            with self.assertRaises(InvalidCurve): Target(self.curve, w, ref, 'bad')

    def test_mutable_inputs_frozen(self):
        u, f, w = [0, 1], [0, 2], [1, 1]
        target = Target(Curve(u, f, 'm', 'N'), w, 2, 'immutable')
        u[0] = -999; f[0] = -999; w[0] = -999
        self.assertEqual(target.curve.displacement, (0, 1))
        self.assertEqual(target.weights, (1, 1))


if __name__ == '__main__':
    unittest.main(verbosity=2)
