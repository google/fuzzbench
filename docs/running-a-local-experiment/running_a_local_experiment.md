---
layout: default
title: Running a local experiment
nav_order: 5
permalink: /running-a-local-experiment
---

# Running a local experiment

**NOTE**: This page explains how to run a local [experiment]({{ site.baseurl }}/reference/glossary/#Experiment) on
your own.

This page assumes a certain level of knowledge about FuzzBench.

- TOC
{:toc}

This page will walk you through on how to use `run_experiment.py`.
Experiments are started by the `run_experiment.py` script. The script will
create and run a dispatcher docker container which runs the experiment,
including:
1. Building desired fuzzer-benchmark combinations.
1. Starting instances to run fuzzing trials with the fuzzer-benchmark
   builds and stopping them when they are done.
1. Measuring the coverage from these trials.
1. Generating reports based on these measurements.

The rest of this page will assume all commands are run from the root of
FuzzBench.

# run_experiment.py

## Experiment configuration file

You need to create an experiment configuration yaml file.
This file contains the configuration parameters for experiments that do not
change very often.
Below is an example configuration file with explanations of each required
parameter.

```yaml
# The number of trials of a fuzzer-benchmark pair to do.
trials: 5

# The amount of time in seconds that each trial is run for.
# 1 day = 24 * 60 * 60 = 86400
max_total_time: 86400

# TODO:
# The location of your docker registry.
# docker_registry: lab-server:5000

# The local experiment folder that will store most of the experiment data.
experiment_filestore: /experiment-data

# The local report folder where HTML reports and summary data will be stored.
report_filestore: /report-data
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

## Viewing reports

You should eventually be able to see reports from your experiment, that are
update at some interval throughout the experiment. However, you may have to wait
a while until they first appear since a lot must happen before there is data to
generate report. Once they are available, you should be able to view them at:
`/report-data/$EXPERIMENT_NAME/index.html`
