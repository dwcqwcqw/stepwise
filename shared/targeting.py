"""Generation targets are constraints to verify, never scores to assign."""
import math
from shared.common import CRITERIA

MAX_TARGET_ATTEMPTS = 3

def target_profile(target):
    """Published integer criterion rows whose equal-weight mean is the target."""
    if not isinstance(target, (int, float)) or isinstance(target, bool) or not math.isfinite(target) or not 4 <= target <= 9 or target * 2 != int(target * 2):
        raise ValueError('Target must be a half band between 4 and 9')
    lower, upper = math.floor(target), math.ceil(target)
    return dict(zip(CRITERIA, [upper, lower, upper, lower]))

def calibration_feedback(assessment, profile):
    """Small, evidence-based revision brief; the next assessor sees none of it."""
    return [{'criterion': c['criterion'], 'intended_band': profile[c['criterion']],
             'assessed_band': c['score'], 'rationale': c['rationale'],
             'next_band_gap': c['higher_band_gap'],
             'target_checks': [{'standard': s['official_standard'], 'match': s['match'],
                               'explanation': s['explanation']}
                              for b in c['band_reviews'] if b['band'] == profile[c['criterion']]
                              for s in b['checks']]}
            for c in assessment['criteria']]
