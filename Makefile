PYTHON ?= python3

.PHONY: check test benchmark-smoke benchmark inventory

check:
	$(PYTHON) -m compileall -q benchmark_harness tests
	$(PYTHON) -m benchmark_harness.cli inventory >/dev/null

test:
	$(PYTHON) -m unittest discover -s tests -v

benchmark-smoke:
	$(PYTHON) -m benchmark_harness.cli smoke
	$(PYTHON) -m benchmark_harness.cli benchmark --profile smoke --implementations cpp,idris2,rust $(BENCHMARK_OPTIONS)

benchmark:
	$(PYTHON) -m benchmark_harness.cli benchmark --profile full --implementations "$(if $(IMPLEMENTATIONS),$(IMPLEMENTATIONS),cpp,idris2)" $(BENCHMARK_OPTIONS)

BENCHMARK_OPTIONS = $(if $(CPP_PATH),--cpp-path "$(CPP_PATH)",) $(if $(CPP_BUILD_PATH),--cpp-build-path "$(CPP_BUILD_PATH)",) $(if $(CPP_COMPILER),--cpp-compiler "$(CPP_COMPILER)",) $(if $(IDRIS2_PATH),--idris2-path "$(IDRIS2_PATH)",) $(if $(IDRIS2_COMPILER),--idris2-compiler "$(IDRIS2_COMPILER)",) $(if $(IDRIS2_BACKEND),--idris2-backend "$(IDRIS2_BACKEND)",) $(if $(RUST_PATH),--rust-path "$(RUST_PATH)",) $(if $(CARGO),--cargo "$(CARGO)",) $(if $(RUSTC),--rustc "$(RUSTC)",)

inventory:
	$(PYTHON) -m benchmark_harness.cli inventory $(if $(CPP_PATH),--cpp-path "$(CPP_PATH)",) $(if $(IDRIS2_PATH),--idris2-path "$(IDRIS2_PATH)",) $(if $(RUST_PATH),--rust-path "$(RUST_PATH)",)
