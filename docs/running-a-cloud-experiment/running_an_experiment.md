---
layout: default
title: Running an experiment
parent: Running an experiment on your Cloud project
nav_order: 2
permalink: /running-a-cloud-experiment/running-an-experiment/
---

# Running an experiment

**NOTE**: Most users of FuzzBench should simply [add a fuzzer]({{ site.baseurl
}}/getting-started/adding-a-new-fuzzer/) and use the FuzzBench service. This
page isn't needed for using the FuzzBench service. This page explains
how to run an [experiment]({{ site.baseurl }}/reference/glossary/#Experiment) on
your own. We don't recommend running experiments on your own for most users.
Validating results from the FuzzBench service is a good reason to run an
experiment on your own.

This page assumes a certain level of knowledge about
Google Cloud and FuzzBench. If you haven't already, please follow the
[guide on setting up a Google Cloud Project]({{ site.baseurl}}/running-your-own-experiment/setting-up-a-google-cloud-project/)
to run your own experiments. This page assumes you already have set up a
Google Cloud Project, since running an experiment requires Google Cloud.

- TOC
{:toc}

This page will walk you through on how to use `run_experiment.py`.
Experiments are started by the `run_experiment.py` script. The script will
create a dispatcher instance on Google Compute Engine which runs the experiment,
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

# The docker registry for your fuzzbench experiments.
# If you use Google Cloud, this can be gcr.io/$PROJECT_NAME.
docker_registry: gcr.io/$PROJECT_NAME

# The name of your Google Cloud project.
cloud_project: $PROJECT_NAME

# The Google Compute Engine zone to run the experiment in.
cloud_compute_zone: $PROJECT_ZONE

# The Google Cloud Storage bucket that will store most of the experiment data.
experiment_filestore: gs://$DATA_BUCKET_NAME

# The Google Cloud Storage bucket where HTML reports and summary data will be stored.
report_filestore: gs://$REPORT_BUCKET_NAME

# The connection to use to connect to the Google Cloud SQL instance.
cloud_sql_instance_connection_name: "$PROJECT_NAME:$PROJECT_REGION:$POSTGRES_INSTANCE=tcp:5432"
```

**NOTE:** The values `$PROJECT_NAME`, `$PROJECT_REGION`, `PROJECT_ZONE`, `$DATA_BUCKET_NAME`,
`$REPORT_BUCKET_NAME` `$POSTGRES_INSTANCE` refer to the values of those
environment variables that were set in the [guide on setting up a Google Cloud
Project]({{ site.baseurl }}/running-your-own-experiment/setting-up-a-google-cloud-project/).
For example if `$PROJECT_NAME` is `my-fuzzbench-project`, use
`my-fuzzbench-project` and not `$PROJECT_NAME`.

## Setting the database password

Find the password for the PostgreSQL instance you are using in your
experiment config.
Set it using the environment variable `POSTGRES_PASSWORD` like so:

```bash
export POSTGRES_PASSWORD="my-super-secret-password"
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

## Viewing reports

You should eventually be able to see reports from your experiment, that are
update at some interval throughout the experiment. However, you may have to wait
a while until they first appear since a lot must happen before there is data to
generate report. Once they are available, you should be able to view them at:
`https://storage.googleapis.com/$REPORT_BUCKET_NAME/$EXPERIMENT_NAME/index.html`

# Advanced usage

## Fuzzer configuration files

Many fuzzers have knobs that affect performance. To make it easier to tweak
these knobs in experiments `run_experiment.py` supports fuzzer configuration
files.
To use a "configured" fuzzer in an experiment, pass the configuration file to
`run_experiment.py` using the `--fuzzer-configs` argument. Below is an example
configuration file with an explanation of how it can configure a fuzzer.

```yaml
# The name of the fuzzer in fuzzers/ we want to run.
fuzzer: libfuzzer

# The name that we want to use for this configuration (e.g. results for this
# configuration show up in reports under the name "libfuzzer_value_profile")
variant_name: libfuzzer_value_profile

# Environment variables that are set before running the fuzzer's fuzzer.py
# script. Note that these have no meaning to fuzzbench, it's up to fuzzer.py
# to do something with them. See fuzzers/libfuzzer/fuzzer.py
# (https://github.com/google/fuzzing/blob/master/fuzzers/libfuzzer/fuzzer.py)
# for how ADDITIONAL_ARGS is used.
env:
  ADDITIONAL_ARGS: -use_value_profile=1

```

Currently values in `env` are only set before running the fuzzer, not before
building the benchmarks or the fuzzer itself.
