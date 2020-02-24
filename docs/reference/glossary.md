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
or random data to a computer program (aka [fuzzing]).

Examples: [libFuzzer](http://libfuzzer.info),
[AFL](http://lcamtuf.coredump.cx/afl/),
[honggfuzz](https://github.com/google/honggfuzz), etc.

### Benchmark

A [fuzz target] that is fuzzed to determine the performance of a fuzzer.

It can be an [OSS-Fuzz project](https://github.com/google/oss-fuzz/tree/master/projects)
([example](https://github.com/google/fuzzbench/blob/master/benchmarks/curl_curl_fuzzer_http/oss-fuzz.yaml))
or a custom one where you explicitly define the steps to checkout code and build
the fuzz target
([example integration](https://github.com/google/fuzzbench/blob/master/benchmarks/vorbis-2017-12-11/build.sh)).

[fuzzing]: https://en.wikipedia.org/wiki/Fuzzing
[fuzz target]: https://github.com/google/fuzzing/blob/master/docs/glossary.md#fuzz-target

