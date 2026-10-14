"""Generation targets are constraints to verify, never scores to assign."""
import math
from shared.common import CRITERIA

MAX_TARGET_ATTEMPTS = 3  # Initial draft plus at most two adjustments.

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

def adjust_writer_profile(current, assessment, desired):
    """Correct the writer's observed level error; never modify assessor scores."""
    observed={c['criterion']:c['score'] for c in assessment['criteria']}
    return {code:max(2,min(9,current[code]+desired[code]-observed[code]))
            for code in CRITERIA}

def nearest_score_profile(assessment, target):
    """Fewest score-level changes needed for the half-up overall estimate."""
    from decimal import Decimal, ROUND_HALF_UP
    scores={c['criterion']:c['score'] for c in assessment['criteria']}
    sums=[s for s in range(37) if float((Decimal(s)/2).quantize(Decimal('1'),rounding=ROUND_HALF_UP)/2)==target]
    remaining=min(sums,key=lambda s:abs(s-sum(scores.values())))-sum(scores.values())
    # Local language edits disturb argument/paragraph structure less than rewrites.
    while remaining:
        for code in ['LR','GRA','TR','CC']:
            direction=1 if remaining>0 else -1
            if 0<=scores[code]+direction<=9:
                scores[code]+=direction;remaining-=direction
            if not remaining:break
    return scores


def apply_focus_edits(essay,edits,protected_position,focus_criteria):
    """Apply bounded exact spans; the model cannot replace a whole essay."""
    if not isinstance(edits,list) or not 1<=len(edits)<=8:
        raise ValueError('Return one to eight short exact replacements')
    spans=[];changed=0
    for edit in edits:
        before=edit.get('before');after=edit.get('after')
        if not isinstance(before,str) or not before or not isinstance(after,str) or before==after or essay.count(before)!=1:
            raise ValueError('Each before span must occur exactly once and change')
        if len(before.split())>25 or len(after.split())>35:
            raise ValueError('Replace short spans, never paragraphs')
        if set(focus_criteria)<={'LR','GRA'} and ('\n' in before or '\n' in after):
            raise ValueError('Language edits must preserve paragraph structure')
        start=essay.index(before);spans.append((start,start+len(before),after))
        changed+=len(before.split())+len(after.split())
    limit=.2 if len(focus_criteria)<=2 else .5
    if changed>len(essay.split())*limit:
        raise ValueError(f'Local edits use {changed} before+after words; maximum {int(len(essay.split())*limit)}. Use fewer edits and short word/phrase replacements, not full sentences.')
    spans.sort()
    if any(a[1]>b[0] for a,b in zip(spans,spans[1:])):
        raise ValueError('Replacement spans must not overlap')
    for start,end,after in reversed(spans):essay=essay[:start]+after+essay[end:]
    if protected_position not in essay:
        raise ValueError('Local edits must preserve the protected position verbatim')
    return essay
