"""Keep each official criterion-band table cell intact as a semantic chunk."""
import json
from shared.common import DATA, ARTIFACTS, digest, jsonl, log, read_json, write_json

def build_chunks(cells: list[dict]) -> list[dict]:
    chunks = []
    for cell in cells:
        content = f"IELTS Academic Writing Task 2 | {cell['criterion_name']} | Band {cell['band']}\n{cell['text']}"
        chunk_id = digest((cell['source_sha256'] + content).encode())
        chunks.append({**cell, "chunk_id": chunk_id, "text": content, "characters": len(content)})
    if len({c['chunk_id'] for c in chunks}) != len(chunks):
        raise ValueError("Duplicate rubric chunks")
    return chunks

def main():
    cells = [json.loads(x) for x in (DATA/'processed/rubric_cells.jsonl').read_text().splitlines()]
    chunks = build_chunks(cells)
    manifest = read_json(DATA/'processed/manifest.json')
    jsonl(DATA/'processed/chunks.jsonl', chunks)
    result = {"source_snapshot": manifest['snapshot_id'], "chunk_snapshot": digest(json.dumps(chunks,sort_keys=True).encode())[:16], "strategy": "criterion_band_table_cell_v1", "overlap": 0, "chunks": len(chunks), "min_characters": min(c['characters'] for c in chunks), "max_characters": max(c['characters'] for c in chunks), "rationale": "A table cell is the smallest complete band-specific judgement. Arbitrary character windows can mix criteria, bands, or Task 1 and Task 2."}
    write_json(DATA/'processed/chunks.manifest.json',result)
    write_json(ARTIFACTS/'chunking.json',result)
    log("chunk_complete", **result)

if __name__ == '__main__': main()
