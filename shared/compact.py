"""Lossless model transport: keep every standard, omit duplicated storage metadata."""
import re

KEYS = {'essay_evidence_id':'e','before_evidence_id':'b','statement_id':'s',
        'limiter_id':'l','subcriterion_id':'d','explanation':'x',
        'band_reviews':'bands','limiters':'limits','judgment':'j',
        'present':'p','higher_band_gap':'gap','next_step':'next'}

def rename(value, keys=KEYS):
    if isinstance(value, dict):return {keys.get(k,k):rename(v,keys) for k,v in value.items()}
    if isinstance(value, list):return [rename(v,keys) for v in value]
    return value

def compact_schema(value):
    """Rename property names and required lists, never enum values or rubric IDs."""
    if isinstance(value,list):return [compact_schema(v) for v in value]
    if not isinstance(value,dict):return value
    result={k:compact_schema(v) for k,v in value.items()}
    if 'properties' in value:
        result['properties']={KEYS.get(k,k):compact_schema(v) for k,v in value['properties'].items()}
    if 'required' in value:result['required']=[KEYS.get(k,k) for k in value['required']]
    return result

def compact_system(system):
    return re.sub(r'\b('+ '|'.join(KEYS) +r')\b',lambda m:KEYS[m[0]],system)+'''\nOutput field names are compact aliases. Input records retain descriptive names: s copies statement_id, l copies limiter_id, d copies subcriterion_id, e selects an essay_evidence evidence_id, and example.b selects its original passage evidence_id. x is the concise explanation. Do not shorten or alter identifier VALUES. All original standards and validation requirements still apply.'''

def expand(value):return rename(value,{v:k for k,v in KEYS.items()})

def rubric_payload(chunks):
    result=[]
    for c in chunks:
        row={k:c[k] for k in ('kind','criterion','band','subcriterion_id') if k in c}
        if c['kind']=='band_descriptor':
            row['statements']=[{k:s[k] for k in ('statement_id','text','conditional','limiting_features') if k in s} for s in c['statements']]
        else:row['text']=c['text']
        result.append(row)
    return result
