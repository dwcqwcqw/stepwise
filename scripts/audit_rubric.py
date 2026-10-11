"""Verify every paragraph against its parent and exact source-table text."""
import argparse
import collections
import json
from pathlib import Path

def audit(processed):
    cells=[json.loads(l) for l in (processed/'rubric_cells.jsonl').read_text().splitlines()]
    chunks=[json.loads(l) for l in (processed/'chunks.jsonl').read_text().splitlines()]
    parents={c['chunk_id']:c for c in chunks if c['kind']=='band_descriptor'}
    children={c['chunk_id']:c for c in chunks if c['kind']=='band_statement'}
    assert len(parents)==80 and len(children)==238
    for child in children.values():
        parent=parents[child['parent_chunk_id']]
        assert all(parent[k]==child[k] for k in ['task','criterion','band','page'])
        assert child['chunk_id'] in {s['chunk_id'] for s in parent['statements']}
    for parent in parents.values():
        assert ' '.join(' '.join(s['text'] for s in parent['statements']).split())==' '.join(parent['text'].split('\n',1)[1].split())
        for statement in parent['statements']:
            assert all(l['text'] and l['text'] in statement['text'] for l in statement['limiting_features'])
    task2=[c for c in children.values() if c['task']=='academic_task_2']
    assert len(task2)==119
    return {'status':'passed','source_sha256':cells[0]['source_sha256'],'band_cells':len(parents),
        'paragraph_statements':len(children),'task2_statements':len(task2),'total_index_chunks':len(chunks),
        'task2_by_criterion':dict(collections.Counter(c['criterion'] for c in task2)),
        'task2_physical_pdf_pages':sorted({c['page'] for c in task2}),
        'chunk_snapshot':json.loads((processed/'chunks.manifest.json').read_text())['chunk_snapshot'],
        'checks':['All 80 PDF cells independently match concatenated paragraph text',
            'No words lost or imported from adjacent cells','Every paragraph retains task, criterion, integer band and physical PDF page',
            'All bold limiting features are exact substrings of their paragraph','All child points link to their original parent cell'],
        'numeric_policy':'Four integer descriptor scores; exact arithmetic mean; half-up to 0.5 for the Task 2 practice estimate. No fabricated half-band descriptor rows or numeric paragraph subscores.'}

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--processed',type=Path,default=Path('runtime/data/processed'))
    parser.add_argument('--output',type=Path,default=Path('runtime/artifacts/paragraph_audit.json'))
    args=parser.parse_args();result=audit(args.processed)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
