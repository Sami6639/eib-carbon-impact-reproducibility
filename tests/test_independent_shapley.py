"""Independently verify published project terms using the subset Shapley formula.

Run after code/run_analysis.py: python tests/test_independent_shapley.py
No production decomposition function is imported. Source-cell agreement is
tested separately by tests/test_analysis.py.
"""
import itertools
import math
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def subset_shapley(old, new):
    n = len(old)
    answer = []
    for k in range(n):
        rest = [j for j in range(n) if j != k]
        contribution = 0.0
        for size in range(n):
            weight = math.factorial(size) * math.factorial(n - size - 1) / math.factorial(n)
            for subset in itertools.combinations(rest, size):
                before = [new[j] if j in subset else old[j] for j in range(n)]
                after = before.copy()
                after[k] = new[k]
                contribution += weight * (math.prod(after) - math.prod(before))
        answer.append(contribution)
    return np.asarray(answer)


class IndependentAttributionTests(unittest.TestCase):
    def test_all_continuing_project_terms(self):
        rows = pd.read_csv(ROOT / 'data/project_report_stream_rows.csv', dtype={'project_id': str})
        terms = pd.read_csv(ROOT / 'results/project_exact_decompositions.csv', dtype={'project_id': str})
        count = 0
        for (period, metric, matched, basis), group in terms.groupby(['period', 'metric', 'matched_only', 'cost_basis']):
            y0, y1 = map(int, period.split('_'))
            a = rows[(rows.report_year == y0) & (rows.stream == 'CAB') & rows.numeric_ghg].set_index('project_id')
            b = rows[(rows.report_year == y1) & (rows.stream == 'CAB') & rows.numeric_ghg].set_index('project_id')
            common = sorted(set(a.index) & set(b.index))
            if matched:
                a, b = a.loc[common], b.loc[common]
            for record in group[group.status == 'numeric_continuer'].itertuples():
                x, y = a.loc[record.project_id], b.loc[record.project_id]
                def factors(z):
                    return [1000 * z[metric + '_ghg_kt_year'], 1 / z.project_cost_eur_m,
                            100 / z.eligible_pct if basis == 'eligible' else 1.0]
                old, new = factors(x), factors(y)
                w0, w1 = x.allocation_eur_m / a.allocation_eur_m.sum(), y.allocation_eur_m / b.allocation_eur_m.sum()
                expected = (w0 + w1) / 2 * subset_shapley(old, new)
                np.testing.assert_allclose(expected, [record.ghg_revision, record.cost_update, record.eligibility_update], rtol=1e-9, atol=1e-8)
                reweight = (math.prod(old) + math.prod(new)) / 2 * (w1 - w0)
                self.assertAlmostEqual(reweight, record.allocation_reweighting, places=7)
                count += 1
        self.assertGreater(count, 0)
        print(f'Independent subset-formula verification: {count} continuing-project/model records, four terms per record.')


if __name__ == '__main__':
    unittest.main(verbosity=2)
