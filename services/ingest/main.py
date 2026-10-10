"""Ingest official assessment knowledge only. MS3 candidates are a separate manifest."""
import json
import re
from pathlib import Path
import httpx
import pymupdf
from shared.common import DATA, ARTIFACTS, CRITERIA, digest, jsonl, log, read_json, write_json

ROOT = Path(__file__).resolve().parents[2]

def collect(source, client):
    path = DATA/'raw'/source['filename']
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        response = client.get(source['url']); response.raise_for_status()
        temporary = path.with_suffix('.part'); temporary.write_bytes(response.content); temporary.replace(path)
    if digest(path.read_bytes()) != source['sha256']:
        raise ValueError(f"Source changed: {source['id']}; audit before updating the lock.")
    log('source_verified', source_id=source['id'], sha256=source['sha256'], bytes=path.stat().st_size)
    return path

def clean(text):
    return re.sub(r'[ \t]+', ' ', text or '').strip()

def record(source, page, text, task='academic_task_2', criterion='ALL', band=None, kind='assessment_detail', **extra):
    return dict(task=task, criterion=criterion, criterion_name=CRITERIA.get(criterion, 'General assessment rules'), band=band, kind=kind, text=clean(text), source_id=source['id'], source_url=source['url'], source_sha256=source['sha256'], source_title=source['id'].replace('-',' ').title(), page=page, version=source['version'], **extra)

def rubric_cells(path, source):
    records=[]
    with pymupdf.open(path) as document:
        for page_no,page in enumerate(document,1):
            text=page.get_text()
            task='academic_task_2' if page_no >= 6 else 'academic_task_1' if page_no >= 2 else 'shared'
            records.append(record(source,page_no,text,task=task,kind='source_page'))
            if 'A script must fully fit' in text:
                instruction=text[text.index('A script must fully fit'):]
                records.append(record(source,page_no,instruction,task=task,kind='rating_rule'))
            for table in page.find_tables().tables:
                rows=table.extract()
                header=' '.join(x or '' for x in rows[0])
                if 'Task Response' not in header and 'Task Achievement' not in header: continue
                codes=list(CRITERIA) if 'Task Response' in header else ['TA','CC','LR','GRA']
                for row_no,row in enumerate(rows[1:],1):
                    score=re.sub(r'\s+','',row[0] or '')
                    if score not in {str(n) for n in range(10)}: continue
                    for col,code in enumerate(codes,1):
                        # Band 0 is one merged rule across all criteria in the source.
                        cell_text=row[1] if score=='0' else row[col]
                        if not clean(cell_text): raise ValueError(f'Empty descriptor {task} {score} {code}')
                        bbox=table.rows[row_no].cells[col] or table.rows[row_no].cells[1]
                        bold=[]
                        if bbox:
                            for block in page.get_text('dict',clip=pymupdf.Rect(bbox))['blocks']:
                                for line in block.get('lines',[]):
                                    for span in line['spans']:
                                        if span['flags'] & 16 and span['text'].strip(): bold.append(span['text'])
                        records.append(record(source,page_no,cell_text,task=task,criterion=code,band=int(score),kind='band_descriptor',limiting_features=bold))
    expected={(task,c,b) for task,codes in [('academic_task_1',['TA','CC','LR','GRA']),('academic_task_2',list(CRITERIA))] for c in codes for b in range(10)}
    observed={(x['task'],x['criterion'],x['band']) for x in records if x['kind']=='band_descriptor'}
    if observed!=expected or sum(x['kind']=='band_descriptor' for x in records)!=80: raise ValueError(f'Incomplete full rubric: {expected-observed}')
    return records

def key_criteria(path, source):
    with pymupdf.open(path) as d: pages=[p.get_text() for p in d]
    records=[record(source,1,pages[0].split('Task 1 \nTASK ACHIEVEMENT')[0],kind='rating_rule')]
    sections={
        'TR':[(2,pages[1].split('TASK RESPONSE (TR)')[1]),(3,pages[2].split('The TR criterion assesses:')[1].split('Task 1 and Task 2')[0])],
        'CC':[(3,pages[2].split('COHERENCE AND COHESION (CC)')[1])],
        'LR':[(4,pages[3].split('LEXICAL RESOURCE (LR)')[1].split('GRAMMATICAL RANGE AND ACCURACY')[0])],
        'GRA':[(4,pages[3].split('GRAMMATICAL RANGE AND ACCURACY (GRA)')[1])]}
    for code,parts in sections.items():
        for page,text in parts:
            records.append(record(source,page,text,criterion=code,kind='criterion_definition'))
            bullets=[clean(x) for x in text.split('▪')[1:] if clean(x)]
            for n,bullet in enumerate(bullets,1):
                records.append(record(source,page,bullet,criterion=code,kind='subcriterion',subcriterion_id=f'{code}-{n}'))
    if sum(x['kind']=='subcriterion' for x in records)!=20: raise ValueError('Expected all 20 official detailed assessment bullets')
    return records

def main():
    sources=read_json(ROOT/'data/sources.lock.json')['sources']; records=[]
    with httpx.Client(follow_redirects=True,timeout=180,headers={'User-Agent':'Mozilla/5.0'},transport=httpx.HTTPTransport(retries=3)) as client:
        for source in sources:
            path=collect(source,client)
            if source['kind']=='band_descriptors': records+=rubric_cells(path,source)
            elif source['kind']=='key_criteria': records+=key_criteria(path,source)
            else:
                with pymupdf.open(path) as d:
                    records += [record(source,n,p.get_text(),criterion='TR',kind='teaching_guidance') for n,p in enumerate(d,1)]
    jsonl(DATA/'processed/rubric_cells.jsonl',records)
    receipts=[{k:s[k] for k in ['id','url','sha256','filename','role','version']} for s in sources]
    manifest={'snapshot_id':digest(json.dumps(receipts,sort_keys=True).encode())[:16],'sources':receipts,'rubric_records':len(records),'descriptor_cells':80,'task2_descriptor_cells':40,'subcriteria':20,'training_candidates_loaded':0,'scope':'All band rules 0–9 for both tasks indexed; scoring constrained to Task 2 and shared rules.'}
    write_json(DATA/'processed/manifest.json',manifest);write_json(ARTIFACTS/'data_quality.json',manifest)
    log('ingest_complete',**manifest)

if __name__=='__main__': main()
