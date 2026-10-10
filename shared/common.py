"""File-based contracts, structured logs, and deterministic identifiers."""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

DATA = Path(os.getenv("DATA_DIR", "/data"))
ARTIFACTS = Path(os.getenv("ARTIFACTS_DIR", "/artifacts"))
CRITERIA = {
    "TR": "Task Response",
    "CC": "Coherence and Cohesion",
    "LR": "Lexical Resource",
    "GRA": "Grammatical Range and Accuracy",
}

def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

def read_json(path: Path):
    return json.loads(path.read_text())

def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)

def jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records))

def log(event: str, **values) -> None:
    print(json.dumps({"at": datetime.now(timezone.utc).isoformat(), "event": event, **values}), flush=True)
