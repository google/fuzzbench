---
layout: default
title: Glossary
nav_order: 1
permalink: /reference/glossary/
parent: Reference
---

# Glossary

For general fuzzing terms, see the [glossary] from [google/fuzzing] project.

[glossary]: https://github.com/google/fuzzing/blob/master/docs/glossary.md
[google/fuzzing]: https://github.com/google/fuzzing

- TOC
{:toc}
---

## FuzzBench specific terms

### Fuzzer

A tool that tries to find interesting inputs by feeding invalid, unexpected,
or random data to a computer program (aka [fuzzing]). Outside of FuzzBench, it's
often called a *fuzzing engine*.

Examples: [libFuzzer](http://libfuzzer.info),
[AFL](http://lcamtuf.coredump.cx/afl/),
[honggfuzz](https://github.com/google/honggfuzz), etc.

### Benchmark

A [fuzz target] that is fuzzed to determine the performance of a fuzzer.

It can be an [OSS-Fuzz project](https://github.com/google/oss-fuzz/tree/master/projects)
([example](https://github.com/google/fuzzbench/blob/master/benchmarks/curl_curl_fuzzer_http/benchmark.yaml))
or a custom one where you explicitly define the steps to checkout the code and
build the fuzz target
([example integration](https://github.com/google/fuzzbench/blob/master/benchmarks/vorbis-2017-12-11/build.sh)).

### Trial

A single run of a particular fuzzer on a particular benchmark. For example, we
might compare AFL and honggfuzz fuzzers by running 20 trials of each on the
libxml2-v2.9.2 benchmark.

### Experiment

A group of [trials](#trial) that are run together to compare fuzzer performance.
This usually includes trials from multiple benchmarks and multiple fuzzers. For
example, to compare libFuzzer, AFL, and honggfuzz, we might run an experiment
where each of them would fuzz every benchmark. Experiments use the same number
of trials for each fuzzer-benchmark pair and a specific amount of time for each
trial (typically, 24 hours) so that results are comparable. FuzzBench generates
reports for experiments while they are running and after they complete.

[fuzzing]: https://en.wikipedia.org/wiki/Fuzzing
[fuzz target]: https://github.com/google/fuzzing/blob/master/docs/glossary.md#fuzz-target

