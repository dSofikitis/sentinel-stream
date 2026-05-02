.PHONY: help all build test lint clean \
        build-generator build-ingest build-parser build-detector build-sink \
        test-generator test-ingest test-parser test-detector test-sink \
        lint-go lint-rust lint-python \
        compose-up compose-down compose-logs compose-build \
        demo demo-from-seed seed schema-check

help: ## list targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  %-22s %s\n", $$1, $$2}'

all: lint test ## lint and test all services

# ---------- build ----------

build: build-generator build-ingest build-parser build-detector build-sink ## build all services

build-generator:
	cd services/generator && pip install --quiet -e .

build-ingest:
	cd services/ingest && go build ./...

build-parser:
	cd services/parser && cargo build --release

build-detector:
	cd services/detector && pip install --quiet -e .

build-sink:
	cd services/sink && go build ./...

# ---------- test ----------

test: test-generator test-ingest test-parser test-detector test-sink ## run all tests

test-generator:
	cd services/generator && pytest -q

test-ingest:
	cd services/ingest && go test ./...

test-parser:
	cd services/parser && cargo test

test-detector:
	cd services/detector && pytest -q

test-sink:
	cd services/sink && go test ./...

# ---------- lint ----------

lint: lint-go lint-rust lint-python ## lint all services

lint-go:
	cd services/ingest && go vet ./...
	cd services/sink   && go vet ./...

lint-rust:
	cd services/parser && cargo fmt --check && cargo clippy --all-targets -- -D warnings

lint-python:
	cd services/generator && ruff check .
	cd services/detector  && ruff check .

# ---------- compose ----------

compose-up: ## bring up redpanda + clickhouse + grafana + ingest
	docker compose -f deploy/compose/docker-compose.yml up -d

compose-down: ## tear down (keeps volumes)
	docker compose -f deploy/compose/docker-compose.yml down

compose-build: ## (re)build container images for ingest + generator
	docker compose -f deploy/compose/docker-compose.yml build

compose-logs: ## tail logs from all services
	docker compose -f deploy/compose/docker-compose.yml logs -f

# ---------- demos ----------

demo: ## end-to-end pipe demo (requires python+rust+go toolchains and jq)
	@echo "Running 5s of synthetic events through generator | parser | detector ..."
	@cd services/generator && python -m sentinel_generator.cli --dry-run --rate 50 --duration 5 --inject brute_force_ssh --seed 1 \
	  | (cd ../parser && cargo run --quiet --release) \
	  | (cd ../detector && python -m sentinel_detector.cli --rules ../../sigma --no-anomaly)

demo-from-seed: ## replay data/sample-events.jsonl through parser | detector (rust + python only)
	@cat data/sample-events.jsonl \
	  | (cd services/parser && cargo run --quiet --release) \
	  | (cd services/detector && python -m sentinel_detector.cli --rules ../../sigma --no-anomaly)

seed: ## post 100 events into the running ingest service via the generator container
	docker compose -f deploy/compose/docker-compose.yml --profile tools run --rm generator \
	  --target http://ingest:8080/events --rate 50 --duration 2 --inject brute_force_ssh

schema-check: ## validate the JSON Schema files parse cleanly
	@python -c "import json,sys,glob; [json.load(open(p)) or print('ok',p) for p in sorted(glob.glob('schemas/*.schema.json'))]"

# ---------- clean ----------

clean: ## remove build artifacts (cargo target/, pytest/ruff caches, build/dist/)
	cd services/parser && cargo clean || true
	rm -rf services/*/.pytest_cache services/*/.ruff_cache services/*/dist services/*/build services/*/*.egg-info
