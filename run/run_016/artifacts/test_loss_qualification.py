"""Synthetic qualification regressions. No files, FE calls, or partner data."""
import math
import unittest
from dataclasses import replace
from inverse.fd_loss import Curve, Target, ScientificEvidence, evaluate, ScientificGateError


class QualificationTests(unittest.TestCase):
    def setUp(self):
        self.target = Target(Curve((0., .5, 1.), (0., 1., 2.), 'm', 'N'),
                             (1., 1., 1.), 2., 'synthetic-qualification-v1')
        self.fe = Curve((0., 1.), (1., 3.), 'm', 'N')
        self.accepted = ScientificEvidence(True, True, True, True, True)

    def score(self, target=None, evidence=None, mode='FORMAL', status='COMPLETED'):
        return evaluate(target or self.target, self.fe, evidence=evidence or self.accepted,
                        fe_status=status, mode=mode)

    def test_mse_not_mean_percentage_error(self):
        result = self.score()
        self.assertEqual(result['loss'], .25)
        self.assertEqual(math.sqrt(result['loss']), .5)
        # At zero experimental force a pointwise percentage error is undefined.

    def test_reference_scaling_is_squared(self):
        other = replace(self.target, force_reference_n=4.)
        self.assertEqual(self.score(other)['loss'], self.score()['loss']/4)

    def test_common_weight_scaling_invariant(self):
        self.assertEqual(self.score(replace(self.target, weights=(7., 7., 7.)))['loss'],
                         self.score()['loss'])

    def test_force_units_gate_cannot_be_inferred_from_si_array_label(self):
        with self.assertRaises(ScientificGateError):
            self.score(evidence=replace(self.accepted, units_and_sign_verified=False))

    def test_warning_fe_still_needs_numerical_acceptance(self):
        with self.assertRaises(ScientificGateError):
            self.score(evidence=replace(self.accepted, numerical_quality_accepted=False),
                       status='COMPLETED_WITH_WARNINGS')

    def test_measurement_declaration_does_not_resolve_conditions(self):
        with self.assertRaises(ScientificGateError):
            self.score(evidence=replace(self.accepted, conditions_matched=False))

    def test_provisional_preserves_unresolved_and_fixed_count(self):
        r = self.score(evidence=ScientificEvidence(), mode='PROVISIONAL')
        self.assertEqual(r['mode'], 'PROVISIONAL')
        self.assertEqual(r['point_count'], 3)
        self.assertEqual(len(r['unresolved']), 5)


if __name__ == '__main__':
    unittest.main(verbosity=2)
