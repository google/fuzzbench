---
layout: default
title: FuzzBench
permalink: /
nav_order: 1
has_children: true
has_toc: false
---

# FuzzBench: Fuzzer Benchmarking As a Service

FuzzBench is a free service that evaluates fuzzers on a wide variety of
real-world benchmarks, at Google scale. The goal of FuzzBench is to make it
painless to rigorously evaluate fuzzing research and make fuzzing research
easier for the community to adopt. We invite members of the research community
to contribute their fuzzers and give us feedback on improving our evaluation
techniques.

FuzzBench provides:

* An easy API for integrating fuzzers.
* Benchmarks from real-world projects, adding an
  [OSS-Fuzz](https://github.com/google/oss-fuzz) benchmark is a three-line
  change.
* A reporting library that produces reports with graphs and statistical tests
  to help you understand the significance of results.

To participate, submit your fuzzer to run on the FuzzBench platform by following
[our simple guide](
https://google.github.io/fuzzbench/getting-started/adding-a-new-fuzzer/).
After your integration is accepted, we will run a large-scale experiment using
your fuzzer and generate a report comparing your fuzzer to others.
See [sample report](https://github.com/google/fuzzbench#sample-report).

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
You can view a sample report
[here](http://www.fuzzbench.com/reports/sample/index.html).
This report is generated using 10 fuzzers against 24 real-world benchmarks,
with 20 trials each and over a duration of 24 hours.

When analyzing reports, we recommend:
* Checking the strengths and weaknesses of a fuzzer against various benchmarks.
* Looking at aggregate results to understand the overall significance of the
  result.

Please provide feedback on any inaccuracies and potential improvements (such as
integration changes, new benchmarks, etc) by opening a GitHub issue
[here](https://github.com/google/fuzzbench/issues/new).

## Documentation
Read our [detailed documentation](https://google.github.io/fuzzbench/) to learn
how to use FuzzBench.

## Contact
Join our [mailing list](https://groups.google.com/g/fuzzbench-users) for
discussions and announcements.

