---
layout: default
title: Contributing code
parent: Getting started
nav_order: 2
permalink: /getting-started/contributing-code/
---

# Contributing code
This page walks you through the process of contributing new code changes to
FuzzBench.

- TOC
{:toc}
---

## Source code structure

* **analysis/** - code for analyzing fuzzer performance using statistical tests.
* **benchmarks/** - benchmarks integrated in the FuzzBench platform (e.g. OpenSSL).
* **common/** - common helper modules (e.g. logging, new process handling, etc).
* **database/** - database handling code.
* **docker/** - Dockerfiles for infra images (does not include fuzzer images).
* **docs/** - this documentation.
* **experiment/** - code for running FuzzBench experiments.
* **experiment/build** - code for building benchmarks and fuzzers for experiments.
* **experiment/measurer** - code for measuring coverage trial coverage.
* **fuzzers/** - fuzzers integrated in the FuzzBench platform (e.g. AFL).
* **service/** - code for the FuzzBench service run by Google.
* **test_libs/** - test helper modules.
* **third_party/** - third-party dependencies (e.g. sancov, oss-fuzz repo).

## Running unit tests

You can run all checks and unit tests for the core functionality using:

```bash
make presubmit
```

You can also run the following to format your code or do different checks
separately:

* `make format` - formats source code using `yapf`.
* `make lint` - runs the linter checks.
* `make typecheck` - runs type checker using `pytype`.
* `make licensecheck` - runs the license header checks.
