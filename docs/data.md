# Data management and quality

Official rubric cells are assessment knowledge. Scored essays are a separate adaptation candidate; they cannot override the rubric or provide expert evaluation labels merely by passing schema checks.

## Collection and extraction

The source lock pins the IELTS PDF checksum and immutable Hugging Face revision/LFS SHA-256. All cached downloads are reverified. `runtime/data/processed/manifest.json` records receipts and a deterministic snapshot ID; raw files are excluded from Git.

PyMuPDF reads only tables headed `Task Response`, excluding Task 1. Extraction requires exactly 24 nonempty cells: four criteria × bands 4–9. Missing or duplicate cells fail the stage. This explicit MVP target range avoids the merged lower-band cells.

Each chunk preserves an entire criterion-band cell, with task, band, criterion, source URL/page/version/hash. Chunk IDs hash source identity plus content. Zero overlap keeps neighboring ratings separate; arbitrary text windows could mix bands or criteria. Length statistics are recorded.

## Essay normalization and splits

Require a nonempty question, at least 40 essay words and numeric four-criterion labels between 0 and 9. Remove exact duplicates using case/whitespace-normalized essay hashes. Preserve original text. Explicitly map upstream `task_achievement_band` to Task 2's `TR` and record the mapping.

Assign all essays sharing a normalized prompt to one train/validation/test bucket by deterministic prompt hash: 80/10/10 by hash buckets, with actual essay proportions reported. This prevents exact prompt leakage. Near-duplicate essays, paraphrased prompt families and prompt/essay mismatches still require an audit before training.

Every record has `training_approved=false`. Record the dataset card's CC BY 4.0 declaration; audit underlying reuse and score provenance before adaptation. Optional GPT advice is not authoritative feedback. MS2 makes no calibrated model-accuracy claim from these candidate labels.

## Index versioning

The chunk snapshot, embedding model, actual ONNX hash, FastEmbed version, dimension and cosine metric determine the index ID and `stepwise_<id>` collection. Stable UUIDs make upserts idempotent. Exact point count is checked before publishing the active index manifest.

Ingest reads source lock -> chunk reads data manifest -> index reads chunk manifest -> API reads index manifest. This records the data version each stage uses. Source changes create distinct index identities; old collections are retained. Automated production retention/rollback belongs to later milestones.
