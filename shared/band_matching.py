"""Complete descriptor coverage and auditable criterion-band decisions."""
from decimal import Decimal, ROUND_HALF_UP
from pydantic import BaseModel, Field
from typing import Literal

class StatementMatch(BaseModel):
    statement_id: str
    match: Literal['meets','not_met','not_applicable']
    explanation: str = Field(min_length=10,max_length=800)
    essay_quote: str = Field(min_length=1,max_length=800)

class LimiterMatch(BaseModel):
    limiter_id: str
    present: bool = Field(strict=True)
    explanation: str = Field(min_length=10,max_length=800)
    essay_quote: str = Field(min_length=1,max_length=800)

class BandReview(BaseModel):
    band: int = Field(ge=0,le=9,strict=True)
    checks: list[StatementMatch] = Field(min_length=1,max_length=12)
    limiters: list[LimiterMatch] = Field(max_length=12)

def score_summary(scores):
    """No intermediate rounding, and no Python banker's rounding at .25/.75."""
    if len(scores)!=4 or any(type(s) is not int or not 0<=s<=9 for s in scores):
        raise ValueError('Four integer criterion scores required')
    mean=Decimal(sum(scores))/Decimal(4)
    band=(mean*2).quantize(Decimal('1'),rounding=ROUND_HALF_UP)/2
    return {'criterion_mean':float(mean),'overall_band':float(band),
        'score_calculation':{'criterion_scores':scores,'sum':sum(scores),'divisor':4,
            'raw_mean':format(mean,'.2f'),'rounded_band':format(band,'.1f'),
            'rounding':'nearest_half_band_half_up','scope':'Task 2 practice estimate'}}

def review_bands(card,essay,context,*,check_score=True):
    code=card['criterion']
    ladder={x['band']:x for x in context['chunks'] if x['kind']=='band_descriptor' and x['criterion']==code}
    reviews=card['band_reviews']
    if len(reviews)!=10 or {r['band'] for r in reviews}!=set(range(10)):
        raise ValueError('Every official band 0–9 must be checked exactly once')
    if set(ladder)!=set(range(10)):raise ValueError('Full Task 2 band ladder required')
    eligible=[];caps=[];result=[]
    for r in sorted(reviews,key=lambda x:x['band']):
        official=ladder[r['band']]
        statements={s['statement_id']:s for s in official.get('statements',[])}
        if not statements:raise ValueError('Official paragraph statements unavailable; rebuild the rubric index')
        if len(r['checks'])!=len(statements) or {s['statement_id'] for s in r['checks']}!=set(statements):
            raise ValueError('Every descriptor statement must be matched once in its own band')
        limiters={l['limiter_id']:l for s in statements.values() for l in s['limiting_features']}
        if len(r['limiters'])!=len(limiters) or {l['limiter_id'] for l in r['limiters']}!=set(limiters):
            raise ValueError('Every bold limiting feature must be checked once in its own band')
        for check in r['checks']:
            standard=statements[check['statement_id']]
            if check['essay_quote'] not in essay:raise ValueError('Band evidence excerpt not in essay')
            if check['match']=='not_applicable' and not standard.get('conditional'):
                raise ValueError(f"Ordinary descriptor requirement {check['statement_id']} at Band {r['band']} cannot be skipped: conditional=false. Re-evaluate it as meets or not_met using the essay; not_applicable is forbidden for this statement.")
            check['official_standard']=standard['text']
            check['source']={k:v for k,v in official.items() if k not in {'statements','limiting_features','characters'}}
            check['source'].update(chunk_id=standard['chunk_id'],kind='band_statement',
                parent_chunk_id=official['chunk_id'],statement_id=standard['statement_id'],
                text=f"IELTS {official['task']} | {official.get('criterion_name',code)} | Band {r['band']} | {standard['statement_id']}\n{standard['text']}")
        for limiter in r['limiters']:
            if limiter['essay_quote'] not in essay:raise ValueError('Limiter evidence excerpt not in essay')
            limiter['official_standard']=limiters[limiter['limiter_id']]['text']
            limiter['source']=official
            # Band 0 is a special eligibility rule, not an inferred plagiarism penalty.
            if limiter['present'] and r['band']>0:caps.append(r['band'])
        r['eligible']=all(s['match']!='not_met' for s in r['checks'])
        if r['band']==0:r['eligible']=all(s['match']=='meets' for s in r['checks'])
        r['source']=official
        if r['eligible']:eligible.append(r['band'])
        result.append(r)
    cap=min(caps,default=9)
    if len(essay.split())<=20:cap=min(cap,1)
    candidates=[b for b in eligible if b<=cap]
    if not candidates:raise ValueError('Band matches do not support any score within the applicable limits')
    derived=max(candidates)
    if check_score and card['score']!=derived:
        raise ValueError(f"Criterion {code} score inconsistent with complete descriptor matches: expected {derived}")
    return result,{'highest_supported_band':derived,'limiting_band_cap':cap,
        'descriptor_statements_checked':sum(len(r['checks']) for r in reviews),
        'rule':'Highest fully supported official integer band, subject to applicable bold limiting features and the 20-word rule.'}
