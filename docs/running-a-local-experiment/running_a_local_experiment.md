---
layout: default
title: Running a local experiment
nav_order: 5
permalink: /running-a-local-experiment
---

# Running a local experiment

This page explains how to run a local [experiment]({{ site.baseurl }}/reference/glossary/#Experiment) on
your own.

- TOC
{:toc}

This page will walk you through on how to use `run_experiment.py` to start
a local experiment. The `run_experiment.py` script will
create and run a dispatcher docker container which runs the experiment,
including:
1. Building desired fuzzer-benchmark combinations.
1. Starting instances to run fuzzing trials with the fuzzer-benchmark
   builds and stopping them when they are done.
1. Measuring the coverage from these trials.
1. Generating reports based on these measurements.

The rest of this page will assume all commands are run from the root of
FuzzBench checkout.

**NOTE**: Currently, there is no resource control in experiment trials (e.g. allocated cpus, memory),
but we do plan to add it in the near future.

## Experiment configuration file

You need to create an experiment configuration yaml file.
This file contains the configuration parameters for experiments that do not
change very often.
Below is an example configuration file with explanations of each required
parameter.

```yaml
# The number of trials of a fuzzer-benchmark pair.
trials: 5

# The amount of time in seconds that each trial is run for.
# 1 day = 24 * 60 * 60 = 86400
max_total_time: 86400

# The location of the docker registry.
# FIXME: Support custom docker registry.
# See https://github.com/google/fuzzbench/issues/777
docker_registry: gcr.io/fuzzbench

# The local experiment folder that will store most of the experiment data.
# Please use an absolute path.
experiment_filestore: /tmp/experiment-data

# The local report folder where HTML reports and summary data will be stored.
# Please use an absolute path.
report_filestore: /tmp/report-data

# Flag that indicates this is a local experiment.
local_experiment: true
```

## Benchmarks

Pick the benchmarks you want to use from the `benchmarks/` directory.

For example: `freetype2-2017` and `bloaty_fuzz_target`.

## Fuzzers

Pick the fuzzers you want to use from the `fuzzers/` directory.
For example: `libfuzzer` and `afl`.

## Executing run_experiment.py

Now that everything is ready, execute `run_experiment.py`:

```bash
PYTHONPATH=. python3 experiment/run_experiment.py \
--experiment-config experiment-config.yaml \
--benchmarks freetype2-2017 bloaty_fuzz_target \
--experiment-name $EXPERIMENT_NAME \
--fuzzers afl libfuzzer
```

where `$EXPERIMENT_NAME` is the name you want to give the experiment.

You can optionally add:
* `--no-seeds` - to skip using seed corpus across all benchmarks.
* `--no-dictionaries` - to skip using dictionaries across all benchmarks.
* `--oss-fuzz-corpus` - use the latest corpora from OSS-Fuzz across all
  benchmarks (where available).
* `--concurrent-builds N` - to limit the number of concurrent builds, useful
  when having limited memory.
* `--runners-cpus` - to limit the number of usable CPUs by the runner containers
  (in which fuzzers run).
* `--measurers-cpus` - to limit the number of usable CPUs by the measurer
  containers.

## Viewing reports

You should eventually be able to see reports from your experiment, that are
update at some interval throughout the experiment. However, you may have to wait
a while until they first appear since a lot must happen before there is data to
generate report. Once they are available, you should be able to view them at:
`/tmp/report-data/$EXPERIMENT_NAME/index.html`.
