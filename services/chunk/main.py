"""Preserve full criterion-band cells and each official detailed assessment bullet."""
import json
from shared.common import DATA, ARTIFACTS, digest, jsonl, log, read_json, write_json

def build_chunks(cells):
    chunks=[]
    for cell in cells:
        label=f"Band {cell['band']}" if cell.get('band') is not None else cell.get('kind','assessment_detail')
        content=f"IELTS {cell.get('task','academic_task_2')} | {cell['criterion_name']} | {label}\n{cell['text']}"
        identity=cell['source_sha256']+str(cell.get('page'))+content
        parent={**cell,'statements':[dict(s) for s in cell.get('statements',[])],'chunk_id':digest(identity.encode()),'text':content,'characters':len(content)}
        chunks.append(parent)
        parent_id=parent['chunk_id']
        for statement in parent['statements']:
            statement_text=f"IELTS {cell['task']} | {cell['criterion_name']} | {label} | {statement['statement_id']}\n{statement['text']}"
            statement['chunk_id']=digest((identity+statement['statement_id']+statement_text).encode())
            chunks.append({**cell,**statement,'kind':'band_statement','statements':[],
                'parent_chunk_id':parent_id,
                'text':statement_text,'characters':len(statement_text)})
    if len({x['chunk_id'] for x in chunks})!=len(chunks): raise ValueError('Duplicate rubric chunks')
    return chunks

def main():
    cells=[json.loads(x) for x in (DATA/'processed/rubric_cells.jsonl').read_text().splitlines()]
    chunks=build_chunks(cells);manifest=read_json(DATA/'processed/manifest.json')
    jsonl(DATA/'processed/chunks.jsonl',chunks)
    result={'source_snapshot':manifest['snapshot_id'],'chunk_snapshot':digest(json.dumps(chunks,sort_keys=True).encode())[:16],'strategy':'pdf_paragraph_statements_with_parent_band_cells_v3','overlap':0,'chunks':len(chunks),'band_statements':sum(c.get('kind')=='band_statement' for c in chunks),'min_characters':min(c['characters'] for c in chunks),'max_characters':max(c['characters'] for c in chunks),'rationale':'Independent PDF paragraphs retain each band feature and its qualifications; bold limiting spans retained. Parent cells and source pages preserve full context. Task metadata prevents Task 1 contamination.'}
    write_json(DATA/'processed/chunks.manifest.json',result);write_json(ARTIFACTS/'chunking.json',result);log('chunk_complete',**result)
if __name__=='__main__': main()
