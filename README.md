# FuzzBench: Fuzzer Benchmarking As a Service

FuzzBench is a service/framework for benchmarking and comparing fuzzers.
It is based on the idea that benchmarking fuzzers should be:
* Painless
* Accurate
* Reproducible

FuzzBench provides:
* An easy API for integrating fuzzers.
* Benchmarks from real projects, adding an OSS-Fuzz benchmark is a three-line
  change.
* Useful reports, with statistical tests to help you understand the significance
  of results.

You can use FuzzBench as a service by integrating a fuzzer using [our simple
guide](https://google.github.io/fuzzbench/getting-started/adding-a-new-fuzzer/).
After your integration is accepted, we will run a large-scale
experiment using your fuzzer (e.g. 20 trials, ~24 benchmarks) and generate
a report comparing your fuzzer to others.
If you'd like to run FuzzBench on your own, you can use our
[guide to running an experiment](https://google.github.io/fuzzbench/advanced-topics/running-an-experiment/).

## Overview
![FuzzBench Service diagram](docs/images/FuzzBench-service.png)

## Documentation
Read our [detailed documentation](https://google.github.io/fuzzbench/) to learn
how to use FuzzBench.

## Sample Report
[Report](https://commondatastorage.googleapis.com/fuzzbench-reports/sample/index.html)
