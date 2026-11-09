"""Reproducible quality scoring (documented in QUALITY_SCORING.md).

A check is (check_id, category, severity, passed, evidence) where passed is
True / False / None (None = could not be executed).

score     = 100 * sum(weight of passed checks) / sum(weight of executed checks)
coverage  = every REQUIRED category for the product type has >= 1 executed check
            and no academic item is left unverified (unless owner-attested)

decision (in this order - a weighted average never hides a critical failure):
  1. any failed CRITICAL check                      -> BLOCKED
  2. any failed MAJOR check                         -> BLOCKED
  3. required coverage missing / unverified items   -> NOT_VERIFIED (no score claimed)
  4. score < target (99.9)                          -> BELOW_TARGET
  5. otherwise                                      -> PASS
"""
WEIGHTS = {'CRITICAL': 10, 'MAJOR': 3, 'MINOR': 1, 'INFO': 0}

REQUIRED = {
    'POWER_TOOL': ['integrity', 'html_structure', 'functionality', 'assets', 'browser_runtime', 'academic'],
    'EXPLAINER_PDF': ['integrity', 'pdf_structure', 'academic', 'visual'],
    'CONCEPT_TILES': ['integrity', 'pdf_structure', 'academic', 'visual'],
    'ANIME_EXPLAINER': ['integrity', 'pdf_structure', 'academic', 'visual'],
    'LIL_DR_BYRD_EXPLAINER': ['integrity', 'pdf_structure', 'academic', 'visual'],
    'EXPLAINER_SOURCE_PACKAGE': ['integrity', 'pdf_structure', 'academic'],
    'BUILT_POWER_TOOL': ['integrity', 'html_structure', 'functionality', 'browser_runtime', 'academic', 'asset_fidelity'],
    'BUILT_EXPLAINER': ['integrity', 'pdf_structure', 'academic', 'asset_fidelity'],
}
DEFAULT_REQUIRED = ['integrity']


def score(checks, product_type, target=99.9, academic_unverified=0, attested=0):
    executed = [c for c in checks if c[3] is not None and WEIGHTS.get(c[2], 0) > 0]
    not_run = [c for c in checks if c[3] is None]
    total_w = sum(WEIGHTS[c[2]] for c in executed)
    passed_w = sum(WEIGHTS[c[2]] for c in executed if c[3])
    value = round(100.0 * passed_w / total_w, 2) if total_w else None
    failed = [c for c in executed if not c[3]]
    crit = [c for c in failed if c[2] == 'CRITICAL']
    major = [c for c in failed if c[2] == 'MAJOR']
    required = REQUIRED.get(product_type, DEFAULT_REQUIRED)
    executed_cats = {c[1] for c in checks if c[3] is not None}
    missing = [r for r in required if r not in executed_cats]
    unverified = max(0, academic_unverified - attested)
    reasons = []
    if crit:
        decision = 'BLOCKED'
        reasons += [f'CRITICAL failed: {c[0]} - {c[4]}' for c in crit]
    if major:
        decision = 'BLOCKED'
        reasons += [f'MAJOR failed: {c[0]} - {c[4]}' for c in major]
    if not crit and not major:
        if missing or unverified or value is None:
            decision = 'NOT_VERIFIED'
            if missing:
                reasons.append(f'Required test categories not executed: {missing}')
            if unverified:
                reasons.append(f'{unverified} academic item(s) could not be deterministically verified '
                               f'and have no owner attestation')
            if value is None:
                reasons.append('No scored checks executed')
        elif value < target:
            decision = 'BELOW_TARGET'
            reasons.append(f'Score {value} below target {target}')
        else:
            decision = 'PASS'
    return {'decision': decision,
            'score': value if decision != 'NOT_VERIFIED' else None,
            'raw_score': value, 'target': target, 'executed_checks': len(executed),
            'not_executed': [c[0] for c in not_run], 'failed': [list(c) for c in failed],
            'critical_failures': len(crit), 'major_failures': len(major),
            'missing_required_categories': missing, 'academic_unverified': unverified,
            'reasons': reasons, 'weights': WEIGHTS, 'required_categories': required,
            'checks': [list(c) for c in checks]}
