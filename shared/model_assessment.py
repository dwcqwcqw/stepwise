"""Two target-blind parallel pairs with full matching and focused explanations."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from shared.common import CRITERIA
from shared.compact import compact_schema, compact_system, expand, rubric_payload
from shared.gemini import generate, ModelUnavailable
from shared.retrieval import assessment_context
from shared.assessment import (REFERENCE_SYSTEM, STRING, obj, arr, reference_schema,
    essay_evidence, resolve_references, validate_assessment, repair_reason)

FAST_SYSTEM=REFERENCE_SYSTEM+'''
Return ONLY the supplied requested_criteria as a keyed object. Each request assesses two criteria; the server combines both independent groups. This is a compact independent assessment, with the same complete official band ladder and limiting rules.
For each criterion, compare EVERY supplied statement in decision_order.statement_ids, in EXACT order. Return matches as M (meets), N (not_met), or A (not_applicable), and one evidence_ids entry per statement in that same order. Ordinary positive requirements cannot be skipped. A is only for an inapplicable conditional special rule. A lower threshold may be met by stronger writing; tolerated weaknesses are allowances, not weaknesses the essay must exhibit. Band 0 requires evidence of its special eligibility condition, never a speculative plagiarism/memorisation allegation.
Return limiter_flags and limiter_evidence_ids in the exact decision_order.limiter_ids order. A present limiting condition caps the criterion at that band's level. Apply the 20-word rule, positive thresholds and actual limiting features. The score must equal the highest fully supported integer band after applicable caps; no half-band criterion scores.
Do not write 119 repetitive explanations. In focus_explanations explain EVERY statement at the assessed band and next band (only Band 9 when score=9), using its exact statement_id and one concise explanation. For limiter_explanations explain every limiter at those two bands, plus every limiter flagged present anywhere. Other bands still require a match and real evidence selection; their hidden explanations are replaced by explicit server decision labels, never invented model reasoning. The next band must have a concrete unmet requirement unless an actual limiting cap explains the score. Do not invent topic-specific prerequisites such as specialist knowledge or citations.
Give one concise rationale, a concrete actionable next_step, one before/after revision, and all supplied qualitative subcriteria per criterion. Rationale 1–2 sentences; match and subcriterion explanations one short sentence. Preserve the original evidence IDs; the server copies exact quotes and official citations. Assess demonstrated writing independently; desired scores, authorship and calibration history are deliberately withheld.
'''


def ordered_records(context,code):
    cells=sorted((c for c in context['chunks'] if c['kind']=='band_descriptor' and c['criterion']==code),key=lambda c:c['band'])
    if [c['band'] for c in cells]!=list(range(10)):
        raise ValueError('Full Task 2 band ladder required')
    statements=[s for c in cells for s in c['statements']]
    limiters=[l for s in statements for l in s['limiting_features']]
    return cells,statements,limiters


def model_schema(evidence,context,codes=None):
    base=reference_schema(evidence)['properties']['criteria']['items']['properties']
    # The paired schema can constrain exact evidence IDs without expanding
    # large fixed-length arrays. Server verification remains mandatory.
    ref={'type':'STRING','enum':[x['evidence_id'] for x in evidence]}
    cards={}
    for code in (codes or CRITERIA):
        _,statements,limiters=ordered_records(context,code)
        props=deepcopy(base);props.pop('criterion')
        props['essay_evidence_id']=ref
        props['example']['properties']['before_evidence_id']=ref
        props['subcriteria']['items']['properties']['essay_evidence_id']=ref
        detail_ids=[c['subcriterion_id'] for c in context['chunks'] if c['kind']=='subcriterion' and c['criterion']==code]
        props['subcriteria']['items']['properties']['subcriterion_id']={'type':'STRING','enum':detail_ids}
        # Exact collection lengths are enforced by the server, not the provider
        # grammar: large fixed arrays can overflow structured-output complexity.
        props.update(matches=arr({'type':'STRING','enum':['M','N','A']}),
            evidence_ids=arr(ref),
            limiter_flags=arr({'type':'BOOLEAN'}),
            limiter_evidence_ids=arr(ref),
            focus_explanations=arr(obj({'statement_id':STRING,'explanation':STRING})),
            limiter_explanations=arr(obj({'limiter_id':STRING,'explanation':STRING})))
        cards[code]=obj(props)
    return compact_schema(obj({'summary':STRING,'criteria':obj(cards)}))


def unpack_matches(value,context):
    """Recover exact statement IDs from the immutable ordered official records."""
    if not isinstance(value.get('criteria'),dict) or set(value['criteria'])!=set(CRITERIA):
        raise ValueError('Exactly four distinct keyed criteria required')
    cards=[]
    labels={'M':'Assessment decision: threshold met.','N':'Assessment decision: threshold not met.','A':'Assessment decision: conditional rule not applicable.'}
    for code in CRITERIA:
        card=deepcopy(value['criteria'][code]);card['criterion']=code
        score=card['score']
        if type(score) is not int or not 0<=score<=9:raise ValueError('Integer criterion score required')
        cells,statements,limiters=ordered_records(context,code)
        matches=card.pop('matches');quotes=card.pop('evidence_ids')
        flags=card.pop('limiter_flags');limiter_quotes=card.pop('limiter_evidence_ids')
        if len(matches)!=len(statements) or len(quotes)!=len(statements):
            raise ValueError(f'{code} requires {len(statements)} ordered statement matches and evidence IDs')
        if len(flags)!=len(limiters) or len(limiter_quotes)!=len(limiters):
            raise ValueError(f'{code} requires {len(limiters)} ordered limiter flags and evidence IDs')
        if any(m not in labels for m in matches) or any(type(f) is not bool for f in flags):
            raise ValueError('Invalid statement decision or limiter flag')
        focus={score,min(9,score+1)}
        expected={s['statement_id'] for c in cells if c['band'] in focus for s in c['statements']}
        reasons=card.pop('focus_explanations');byid={x['statement_id']:x['explanation'] for x in reasons}
        if len(reasons)!=len(expected) or set(byid)!=expected:
            raise ValueError(f'{code} must explain assessed/next-band statements exactly once; required IDs: {sorted(expected)}; received IDs: {sorted(byid)}')
        needed_limiters={l['limiter_id'] for c in cells if c['band'] in focus for s in c['statements'] for l in s['limiting_features']}
        needed_limiters.update(l['limiter_id'] for l,present in zip(limiters,flags) if present)
        reasons=card.pop('limiter_explanations');limiter_reasons={x['limiter_id']:x['explanation'] for x in reasons}
        if len(reasons)!=len(needed_limiters) or set(limiter_reasons)!=needed_limiters:
            raise ValueError(f'{code} must explain assessed/next-band and present limiters exactly once; required IDs: {sorted(needed_limiters)}')
        decisions={s['statement_id']:{'statement_id':s['statement_id'],'match':{'M':'meets','N':'not_met','A':'not_applicable'}[m],
            'essay_evidence_id':q,'explanation':byid.get(s['statement_id'],labels[m])} for s,m,q in zip(statements,matches,quotes)}
        caps={l['limiter_id']:{'limiter_id':l['limiter_id'],'present':p,'essay_evidence_id':q,
            'explanation':limiter_reasons.get(l['limiter_id'],'Assessment decision: limiting condition '+('present.' if p else 'absent.'))} for l,p,q in zip(limiters,flags,limiter_quotes)}
        card['band_reviews']=[{'band':c['band'],'checks':[decisions[s['statement_id']] for s in c['statements']],
            'limiters':[caps[l['limiter_id']] for s in c['statements'] for l in s['limiting_features']]} for c in cells]
        cards.append(card)
    return {'summary':value['summary'],'criteria':cards}


def assess_model_essay(prompt,essay,progress=None):
    emit=progress or (lambda **event:None)
    emit(phase='retrieval',status='running',message='Retrieving the full official band standards')
    context=assessment_context(prompt+' '+essay[:2000]);evidence=essay_evidence(essay)
    order={code:{'statement_ids':[s['statement_id'] for s in ordered_records(context,code)[1]],
        'limiter_ids':[l['limiter_id'] for l in ordered_records(context,code)[2]]} for code in CRITERIA}
    count=sum(len(v['statement_ids']) for v in order.values())
    emit(phase='retrieval',status='done',message=f'All {count} Task 2 standards retrieved',statements=count)
    payload={'question':prompt,'essay':essay,'essay_evidence':evidence,'word_count':len(essay.split()),
        'official_assessment_context':rubric_payload(context['chunks']),'decision_order':order}
    calls=[]
    emit(phase='assessment',status='running',message='Reviewing two pairs of criteria in parallel')
    for attempt in range(2):
        def group(codes):
            selected={**payload,'requested_criteria':list(codes),
                'official_assessment_context':[c for c in payload['official_assessment_context'] if c.get('criterion') in codes],
                'decision_order':{k:v for k,v in order.items() if k in codes}}
            wire,receipt=generate(compact_system(FAST_SYSTEM),selected,model_schema(evidence,context,codes),temperature=.1)
            value=expand(wire)
            if not isinstance(value.get('criteria'),dict) or set(value['criteria'])!=set(codes):
                raise ModelUnavailable('The assessment returned incomplete criterion groups; please retry.')
            return value,{**receipt,'criteria':list(codes)}
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs=[pool.submit(copy_context().run,group,codes) for codes in [('TR','CC'),('LR','GRA')]]
            groups=[job.result() for job in jobs]
        calls.extend(receipt for _,receipt in groups)
        combined={'summary':' '.join(value['summary'] for value,_ in groups),
            'criteria':{k:v for value,_ in groups for k,v in value['criteria'].items()}}
        wire=combined
        emit(phase='validation',status='running',message='Checking all band decisions, quotes and exact score arithmetic')
        try:
            canonical=unpack_matches(combined,context)
            resolved=resolve_references(canonical,evidence,context)
            result=validate_assessment(resolved,essay,context)
        except (ValueError,KeyError,TypeError) as error:
            payload['validation_repair']=repair_reason(error);payload['previous_assessment']=wire
            emit(phase='assessment',status='repair',message='Rechecking the combined assessment evidence')
            continue
        for c in result['criteria']:
            emit(phase='assessment',status='done',criterion=c['criterion'],message=f"{CRITERIA[c['criterion']]} checked")
        result.update(model_calls=calls,descriptor_statements_checked=count,
            evidence_strategy='all_band_matches_two_parallel_pairs_with_assessed_and_next_band_explanations',
            explanation_scope='Assessed and next band plus present limiters; other bands retain explicit decision labels and exact evidence.',
            assessment_mode='compact_parallel_pairs')
        emit(phase='validation',status='done',message='Official matches, evidence and four-score average verified')
        return result
    raise ModelUnavailable('The combined assessment could not verify its evidence. Please try again; your writing is unchanged.')
