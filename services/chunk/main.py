"""Preserve full criterion-band cells and each official detailed assessment bullet."""
import json
from shared.common import DATA, ARTIFACTS, digest, jsonl, log, read_json, write_json

def build_chunks(cells):
    chunks=[]
    for cell in cells:
        label=f"Band {cell['band']}" if cell.get('band') is not None else cell.get('kind','assessment_detail')
        content=f"IELTS {cell.get('task','academic_task_2')} | {cell['criterion_name']} | {label}\n{cell['text']}"
        identity=cell['source_sha256']+str(cell.get('page'))+content
        chunks.append({**cell,'chunk_id':digest(identity.encode()),'text':content,'characters':len(content)})
    if len({x['chunk_id'] for x in chunks})!=len(chunks): raise ValueError('Duplicate rubric chunks')
    return chunks

def main():
    cells=[json.loads(x) for x in (DATA/'processed/rubric_cells.jsonl').read_text().splitlines()]
    chunks=build_chunks(cells);manifest=read_json(DATA/'processed/manifest.json')
    jsonl(DATA/'processed/chunks.jsonl',chunks)
    result={'source_snapshot':manifest['snapshot_id'],'chunk_snapshot':digest(json.dumps(chunks,sort_keys=True).encode())[:16],'strategy':'full_rubric_cells_definitions_subcriteria_pages_v2','overlap':0,'chunks':len(chunks),'min_characters':min(c['characters'] for c in chunks),'max_characters':max(c['characters'] for c in chunks),'rationale':'Complete band 0–9 cells, intact rating rules, all 20 detailed subcriteria; full source pages retained for coverage. Task metadata prevents Task 1 contamination.'}
    write_json(DATA/'processed/chunks.manifest.json',result);write_json(ARTIFACTS/'chunking.json',result);log('chunk_complete',**result)
if __name__=='__main__': main()
