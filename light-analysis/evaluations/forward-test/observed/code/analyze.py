"""Reproduce this retrospective synthetic-fixture analysis; no experiments or network.
Run from this workspace with: python -X utf8 code/analyze.py
Only writes derived/results.json and derived/task-summary.csv within this workspace.
"""
import csv
import hashlib
import json
import math
import platform
import statistics
import sys
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
import scipy
from scipy.stats import t

ROOT = Path(__file__).resolve().parents[1]
context = json.loads((ROOT / 'context.json').read_text(encoding='utf-8-sig'))
plan = json.loads((ROOT / 'analysis-plan.json').read_text(encoding='utf-8-sig'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def check(condition, message):
    if not condition:
        raise ValueError(message)

sources = []
for item in context['inputs']:
    snapshot = ROOT / 'inputs' / Path(item['path']).name
    check(sha(snapshot) == item['sha256'], 'Frozen copy mismatch: ' + item['input_id'])
    original = Path(item['path'])
    if original.exists():
        check(sha(original) == item['sha256'], 'Original input drift: ' + item['input_id'])
    sources.append({'input_id': item['input_id'], 'original_path': item['path'],
                    'frozen_copy': str(snapshot.relative_to(ROOT)),
                    'sha256': sha(snapshot), 'bytes': snapshot.stat().st_size})

score_path = ROOT / 'inputs' / 'scores.csv'
with score_path.open(encoding='utf-8-sig', newline='') as handle:
    reader = csv.DictReader(handle)
    check(reader.fieldnames == ['task', 'seed', 'method', 'score'], 'Unexpected columns')
    rows = [{**row, 'csv_line': line} for line, row in enumerate(reader, 2)]
expected_tasks = ['T01', 'T02', 'T03', 'T04']
expected_keys = {(task, method, seed) for task in expected_tasks
                 for method in ('A', 'B') for seed in ('1', '2', '3')}
actual_keys = [(r['task'], r['method'], r['seed']) for r in rows]
check(len(rows) == 24 and len(set(actual_keys)) == 24, 'Missing/duplicate rows')
check(set(actual_keys) == expected_keys, 'Plan/actual matrix mismatch')
for row in rows:
    row['value'] = float(row['score'])
    check(math.isfinite(row['value']) and 0 <= row['value'] <= 1, 'Invalid accuracy')

summaries = []
components = []
for task in expected_tasks:
    cell = {}
    for method in ('A', 'B'):
        selected = [r for r in rows if r['task'] == task and r['method'] == method]
        values = [r['value'] for r in selected]
        cell[method] = {'n': len(values), 'mean': statistics.mean(values),
                        'sample_sd': statistics.stdev(values),
                        'sample_variance': statistics.variance(values),
                        'raw_csv_lines': [r['csv_line'] for r in selected]}
        components.append({'task': task, 'method': method,
                           'variance_contribution': (1 / 4) ** 2 * cell[method]['sample_variance'] / len(values),
                           'degrees_of_freedom': len(values) - 1})
    difference = cell['A']['mean'] - cell['B']['mean']
    summaries.append({'task': task, 'A': cell['A'], 'B': cell['B'],
                      'difference_accuracy': difference, 'difference_pp': difference * 100})

mean_a = statistics.mean(s['A']['mean'] for s in summaries)
mean_b = statistics.mean(s['B']['mean'] for s in summaries)
effects = [s['difference_accuracy'] for s in summaries]
effect = statistics.mean(effects)
variance = sum(c['variance_contribution'] for c in components)
se = math.sqrt(variance)
df = variance ** 2 / sum(c['variance_contribution'] ** 2 / c['degrees_of_freedom'] for c in components)
critical = float(t.ppf(0.975, df))
finite_ci = [effect - critical * se, effect + critical * se]
between_sd = statistics.stdev(effects)
task_se = between_sd / math.sqrt(4)
task_critical = float(t.ppf(0.975, 3))
task_interval = [effect - task_critical * task_se, effect + task_critical * task_se]
leave_one_out = [{'omitted_task': s['task'], 'n_tasks_remaining': 3,
                  'mean_difference_accuracy': statistics.mean(v for i, v in enumerate(effects) if i != j)}
                 for j, s in enumerate(summaries)]

# Independent exact-rational check reads the raw strings, rather than rounded cell outputs.
exact = {}
exact_components = []
for task in expected_tasks:
    exact[task] = {}
    for method in ('A', 'B'):
        vals = [Fraction(r['score']) for r in rows if (r['task'], r['method']) == (task, method)]
        avg = sum(vals) / len(vals)
        sample_var = sum((v - avg) ** 2 for v in vals) / (len(vals) - 1)
        exact[task][method] = avg
        exact_components.append(sample_var / (len(vals) * 16))
exact_effects = {task: exact[task]['A'] - exact[task]['B'] for task in expected_tasks}
exact_effect = sum(exact_effects.values()) / 4
check(math.isclose(effect, float(exact_effect), abs_tol=1e-15), 'Exact macro cross-check failed')
check(math.isclose(variance, float(sum(exact_components)), rel_tol=1e-12), 'Variance formula cross-check failed')
for row in leave_one_out:
    expected = sum(v for task, v in exact_effects.items() if task != row['omitted_task']) / 3
    check(math.isclose(row['mean_difference_accuracy'], float(expected), abs_tol=1e-15), 'Deletion cross-check failed')

# A separate Simpson quadrature checks the Student-t quantiles used by SciPy.
def cdf_by_quadrature(x, dof):
    n = 4000
    width = x / n
    normalizer = math.gamma((dof + 1) / 2) / (math.sqrt(dof * math.pi) * math.gamma(dof / 2))
    def density(y):
        return normalizer * (1 + y * y / dof) ** (-(dof + 1) / 2)
    total = density(0) + density(x)
    total += 4 * sum(density(i * width) for i in range(1, n, 2))
    total += 2 * sum(density(i * width) for i in range(2, n, 2))
    return 0.5 + width * total / 3
cdf_fixed = cdf_by_quadrature(critical, df)
cdf_task = cdf_by_quadrature(task_critical, 3)
check(abs(cdf_fixed - 0.975) < 1e-9 and abs(cdf_task - 0.975) < 1e-9, 'Student-t quantile check failed')

result = {
    'data_kind': 'synthetic_validation',
    'analysis_timing': plan['timing'],
    'sources': sources,
    'audit': {'expected_rows': 24, 'actual_rows': len(rows), 'tasks': expected_tasks,
              'methods': ['A', 'B'], 'runs_per_task_method': 3,
              'missing_rows': 0, 'duplicate_keys': 0, 'invalid_scores': 0,
              'excluded_rows': 0, 'seed_pairing': False,
              'process_successes': 24, 'process_success_basis': 'Protocol only; no logs supplied',
              'task_probability_sample': False, 'domain_confidence_interval_identified': False},
    'task_summaries': summaries,
    'fixed_task_macro': {'mean_A': mean_a, 'mean_B': mean_b,
                         'mean_difference_accuracy': effect, 'mean_difference_pp': effect * 100,
                         'threshold_accuracy': 0.01, 'gap_below_threshold_accuracy': 0.01 - effect,
                         'n_tasks': 4, 'n_training_runs': 24, 'observed_positive_tasks': 2,
                         'observed_negative_tasks': 2, 'between_task_effect_sd_accuracy': between_sd},
    'conditional_training_interval': {
        'level': 0.95, 'lower': finite_ci[0], 'upper': finite_ci[1],
        'standard_error': se, 'welch_satterthwaite_df': df, 'critical_t': critical,
        'variance_components': components,
        'method': 'Fixed-task equal-weight contrast; independent cell variances; approximate Welch-Satterthwaite t',
        'scope': 'Training randomness on these four fixed tasks/splits only; no domain, test-example or selection coverage',
        'assumptions': 'Independent training runs/cells; approximately normal cell scores; n=3 cannot validate distribution',
        'epistemic_status': 'Retrospective exploratory calculation on synthetic validation data'},
    'hypothetical_task_sampling_sensitivity': {
        'level': 0.95, 'lower': task_interval[0], 'upper': task_interval[1],
        'n_tasks': 4, 'df': 3, 'standard_error': task_se, 'critical_t': task_critical,
        'method': 't interval on four task mean differences',
        'scope': 'Hypothetical iid representative-task sampling and suitable task-effect model',
        'valid_domain_coverage_claim': False,
        'reason': 'Known convenience selection; task representativeness and t-model assumptions unsupported'},
    'leave_one_task_out': leave_one_out,
    'numeric_checks': {'exact_macro_fraction': str(exact_effect),
                       'exact_task_effects': {k: str(v) for k, v in exact_effects.items()},
                       'exact_macro_variance_fraction': str(sum(exact_components)),
                       'quantile_cdf_by_independent_quadrature_fixed': cdf_fixed,
                       'quantile_cdf_by_independent_quadrature_task': cdf_task,
                       'macro_variance_deletion_checks_passed': True},
    'execution': {'utc_time': datetime.now(timezone.utc).isoformat(),
                  'command': 'python -X utf8 code/analyze.py', 'cwd': str(ROOT),
                  'python_executable': sys.executable, 'python': sys.version,
                  'platform': platform.platform(), 'scipy': scipy.__version__,
                  'randomness': 'None; deterministic calculation, no resampling',
                  'analysis_code_sha256': sha(Path(__file__)),
                  'plan_sha256': sha(ROOT / 'analysis-plan.json')}
}
(ROOT / 'derived').mkdir(exist_ok=True)
(ROOT / 'derived' / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
with (ROOT / 'derived' / 'task-summary.csv').open('w', encoding='utf-8', newline='') as handle:
    writer = csv.writer(handle)
    writer.writerow(['task', 'n_A', 'mean_A', 'sample_SD_A', 'n_B', 'mean_B', 'sample_SD_B', 'A_minus_B_accuracy', 'A_minus_B_pp', 'raw_CSV_lines_A', 'raw_CSV_lines_B'])
    for s in summaries:
        writer.writerow([s['task'], s['A']['n'], s['A']['mean'], s['A']['sample_sd'], s['B']['n'], s['B']['mean'], s['B']['sample_sd'], s['difference_accuracy'], s['difference_pp'], '|'.join(map(str, s['A']['raw_csv_lines'])), '|'.join(map(str, s['B']['raw_csv_lines']))])
print(json.dumps({'macro_difference': effect, 'fixed_task_conditional_95_interval': finite_ci,
                  'hypothetical_task_interval': task_interval, 'numerical_checks': 'passed'}, ensure_ascii=False))
