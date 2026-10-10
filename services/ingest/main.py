"""Download pinned sources, validate essays, extract Task 2 rubric table cells."""
import json
import re
import sys
from pathlib import Path
import httpx
import pymupdf
import pyarrow.parquet as pq
from shared.common import DATA, ARTIFACTS, CRITERIA, digest, jsonl, log, read_json, write_json

ROOT = Path(__file__).resolve().parents[2]

def collect(source: dict, client: httpx.Client) -> Path:
    path = DATA / "raw" / source["filename"]
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        response = client.get(source["url"])
        response.raise_for_status()
        temporary = path.with_suffix(path.suffix + ".part")
        temporary.write_bytes(response.content)
        temporary.replace(path)
    actual = digest(path.read_bytes())
    if actual != source["sha256"]:
        raise ValueError(f"Source changed: {source['id']}; expected {source['sha256']}, got {actual}. Audit a new version before updating sources.lock.json.")
    log("source_verified", source_id=source["id"], sha256=actual, bytes=path.stat().st_size)
    return path

def rubric_cells(path: Path, source: dict) -> list[dict]:
    cells = []
    # Detect Task Response table headers: this excludes Task 1 automatically.
    with pymupdf.open(path) as document:
        for page_no, page in enumerate(document, 1):
            if "Task Response" not in page.get_text():
                continue
            for table in page.find_tables().tables:
                rows = table.extract()
                if not rows or "Task Response" not in " ".join(x or "" for x in rows[0]):
                    continue
                for row in rows[1:]:
                    score = re.sub(r"\s+", "", row[0] or "")
                    if score not in {str(x) for x in range(4, 10)} or len(row) < 5:
                        continue
                    for code, text in zip(CRITERIA, row[1:5], strict=True):
                        text = re.sub(r"[ \t]+", " ", (text or "").replace("\r", "")).strip()
                        if not text:
                            raise ValueError(f"Empty rubric cell: page {page_no}, band {score}, {code}")
                        cells.append({"task": "academic_task_2", "criterion": code, "criterion_name": CRITERIA[code], "band": int(score), "text": text, "source_id": source["id"], "source_url": source["url"], "source_sha256": source["sha256"], "page": page_no, "version": "May 2023"})
    expected = {(c, b) for c in CRITERIA for b in range(4, 10)}
    observed = {(r["criterion"], r["band"]) for r in cells}
    # MVP target bands are 4-9. Lower merged cells are deliberately excluded.
    if observed != expected or len(cells) != len(expected):
        raise ValueError(f"Incomplete rubric extraction: missing {sorted(expected-observed)}")
    return cells

def normalize_essays(path: Path) -> tuple[list[dict], dict]:
    rows = pq.read_table(path).to_pylist()
    fields = {"TR": "task_achievement_band", "CC": "coherence_cohesion_band", "LR": "lexical_resource_band", "GRA": "grammatical_range_band"}
    valid, rejected, duplicates, seen = [], [], 0, set()
    for row in rows:
        prompt = re.sub(r"\s+", " ", str(row.get("question") or "")).strip()
        essay = str(row.get("essay_text") or "").strip()
        identity = digest(re.sub(r"\s+", " ", essay.lower()).encode())
        scores = {c: row.get(f) for c, f in fields.items()}
        if not prompt or len(essay.split()) < 40 or any(not isinstance(v, (float,int)) or not 0 <= v <= 9 for v in scores.values()):
            rejected.append(str(row.get("essay_id", "unknown")))
            continue
        if identity in seen:
            duplicates += 1
            continue
        seen.add(identity)
        prompt_id = digest(prompt.lower().encode())
        # All essays with the same normalized prompt stay in one split.
        bucket = int(prompt_id[:8],16) % 10
        split = "test" if bucket == 0 else "validation" if bucket == 1 else "train"
        valid.append({"essay_id": str(row.get("essay_id")), "prompt_id": prompt_id, "essay_sha256": identity, "prompt": prompt, "essay": essay, "word_count": len(essay.split()), "overall_band": row.get("overall_band"), "criterion_scores": scores, "split": split, "label_source": "Writing9-derived; provenance audit pending", "training_approved": False})
    stats = {"source_rows": len(rows), "valid_unique_rows": len(valid), "exact_duplicates_removed": duplicates, "invalid_rows": len(rejected), "unique_prompts": len({r['prompt_id'] for r in valid}), "splits": {s: sum(r["split"]==s for r in valid) for s in ['train','validation','test']}, "schema_mapping": fields, "training_approved": False, "notes": "Task 2 candidate corpus. No essays or GPT advice enter the official-rubric vector collection. Automated scores are not used as expert test labels. Near-duplicate and prompt-family checks remain before training."}
    return valid, stats

def main() -> None:
    lock = read_json(ROOT / "data/sources.lock.json")
    receipts, cells, essay_stats = [], [], {}
    with httpx.Client(follow_redirects=True, timeout=180, transport=httpx.HTTPTransport(retries=3)) as client:
        for source in lock["sources"]:
            path = collect(source, client)
            receipts.append({k: source[k] for k in ['id','url','sha256','filename','role']})
            if source["role"] == "rubric":
                cells.extend(rubric_cells(path, source))
            elif source["role"] == "training_candidate":
                essays, essay_stats = normalize_essays(path)
                jsonl(DATA / "processed/essays.jsonl", essays)
    jsonl(DATA / "processed/rubric_cells.jsonl", cells)
    manifest = {"snapshot_id": digest(json.dumps(receipts,sort_keys=True).encode())[:16], "sources": receipts, "rubric_cells": len(cells), "essay_quality": essay_stats}
    write_json(DATA / "processed/manifest.json", manifest)
    write_json(ARTIFACTS / "data_quality.json", manifest)
    log("ingest_complete", snapshot_id=manifest["snapshot_id"], rubric_cells=len(cells), **essay_stats)

if __name__ == "__main__":
    main()
