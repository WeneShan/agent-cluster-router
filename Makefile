# Agent Cluster Router — Makefile
# v5.3: Test layering — unit → integration → e2e

.PHONY: test test-unit test-integration test-e2e test-all eval clean

PYTEST = python3 -m pytest

# ─── Fast (default) — unit + integration, no e2e ───
test: test-unit test-integration

# ─── Unit only — no server, no network, ~200ms ───
test-unit:
	$(PYTEST) -m unit -v --tb=short

# ─── Integration — TestClient, no real backends ───
test-integration:
	$(PYTEST) -m integration -v --tb=short

# ─── E2E — requires server + real backends running ───
# Run: make start-server && make test-e2e
test-e2e:
	$(PYTEST) -m e2e -v --tb=long --timeout=180

# ─── ALL tests (CI mode — skip e2e by default) ───
test-all:
	$(PYTEST) -m "not e2e" -v --tb=short

# ─── CI target — same as test-all but stricter ───
ci: test-all
	@echo "CI: All non-e2e tests passed."

# ─── Eval — dry_run routing accuracy (needs server) ───
eval:
	python3 evals/run_eval.py

# ─── Start/stop server ───
start-server:
	bash start.sh

stop-server:
	bash stop.sh

# ─── Clean ───
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache
	@echo "Clean done."
