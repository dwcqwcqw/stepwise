.PHONY: run stop logs test verify evidence
run:
	bash scripts/run.sh
stop:
	docker compose down
logs:
	docker compose logs --no-color
test:
	uv run --directory services/api --group dev pytest ../../tests/unit -q
verify:
	python3 scripts/verify.py
evidence:
	bash scripts/evidence.sh
