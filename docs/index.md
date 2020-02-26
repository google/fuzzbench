---
layout: default
title: FuzzBench
permalink: /
nav_order: 1
has_children: true
has_toc: false
---

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
guide]({{ site.baseurl }}/getting-started/adding-a-new-fuzzer/).
After your integration is accepted, FuzzBench will run a large-scale
experiment using your fuzzer (e.g. 20 trials, ~24 benchmarks) and generate
a report comparing your fuzzer to other fuzzers.
If you'd like to run FuzzBench on your own, you can use our
[guide to running an experiment]({{ site.baseurl }}/advanced-topics/running-an-experiment/).

## Overview

![FuzzBench Service diagram](images/FuzzBench-service.png)
The process works like this:
1. A developer of a fuzzer (or someone else interested)
[integrates]({{ site.baseurl }}/getting-started/adding-a-new-fuzzer/) their
fuzzer with FuzzBench.
1. The integration is merged into the official FuzzBench repo.
1. FuzzBench runs an experiment with the new fuzzer on the benchmarks.
1. FuzzBench publishes a report comparing the performance of the fuzzer to other
fuzzers both on individual benchmarks and in aggregate.

## Sample Report

[Report](https://commondatastorage.googleapis.com/fuzzbench-reports/sample/index.html)

