PYTHON ?= python3

.PHONY: check test benchmark-smoke benchmark inventory

check:
	$(PYTHON) -m compileall -q benchmark_harness tests
	$(PYTHON) -m benchmark_harness.cli inventory >/dev/null

test:
	$(PYTHON) -m unittest discover -s tests -v

benchmark-smoke:
	$(PYTHON) -m benchmark_harness.cli smoke
	$(PYTHON) -m benchmark_harness.cli benchmark --profile smoke --implementations cpp $(if $(CPP_PATH),--cpp-path "$(CPP_PATH)",) $(if $(CPP_BUILD_PATH),--cpp-build-path "$(CPP_BUILD_PATH)",) $(if $(CPP_COMPILER),--cpp-compiler "$(CPP_COMPILER)",)

benchmark:
	$(PYTHON) -m benchmark_harness.cli benchmark --profile full --implementations "$(if $(IMPLEMENTATIONS),$(IMPLEMENTATIONS),cpp)" $(if $(CPP_PATH),--cpp-path "$(CPP_PATH)",) $(if $(CPP_BUILD_PATH),--cpp-build-path "$(CPP_BUILD_PATH)",) $(if $(CPP_COMPILER),--cpp-compiler "$(CPP_COMPILER)",)

inventory:
	$(PYTHON) -m benchmark_harness.cli inventory $(if $(CPP_PATH),--cpp-path "$(CPP_PATH)",) $(if $(IDRIS2_PATH),--idris2-path "$(IDRIS2_PATH)",) $(if $(RUST_PATH),--rust-path "$(RUST_PATH)",)
