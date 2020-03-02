---
layout: default
title: How it works
parent: Reference
nav_order: 3
permalink: /reference/how-it-works/
---

# How it works
{: .no_toc}

This document provides a high-level description of how FuzzBench works
end-to-end. It isn't necessary for users of the FuzzBench service to know
most of these details.

- TOC
{:toc}

---

## Overview


![FuzzBench architecture]({{site.baseurl}}/images/FuzzBench-architecture.png)

## Dispatcher

As mentioned in the [guide to running an experiment]({{
site.baseurl}}/running-your-own-experiment/running-an-experiment/),
`run_experiment.py` creates a [Google Compute Engine
instance](https://cloud.google.com/compute) called the dispatcher to run an
experiment. In addition to referring to the instance, "dispatcher" can also
refer to the [script/process the instance
runs](https://github.com/google/fuzzbench/blob/master/experiment/dispatcher.py).
The dispatcher (script) doesn't actually do much on its own. It does some
basic initialization like saving details about the experiment to the database
and then starts four other major components - the builder, the scheduler, the
measurer, and the reporter. All of these components run on the dispatcher
instance.

## Builder

The
[builder](https://github.com/google/fuzzbench/blob/master/experiment/builder.py)
produces a build for each fuzzer-benchmark
pair needed by the experiment and does a coverage build for each benchmark.
The builder uses the [Google Cloud Build](https://cloud.google.com/cloud-build)
service for building the docker images needed by the experiment since it is
faster and simpler than building them on Compute Engine instances. When the
builder finishes doing the needed builds, it terminates. Thus, unlike other
components, it isn't running for the duration of an experiment.

### Builds

Details on how builds work are provided in the [guide to adding a fuzzer]({{
site.baseurl}}/getting-started/adding-a-fuzzer/) and the [guide to adding a
benchmark]({{ site.baseurl}}/developing-fuzzbench/adding-a-benchmark/).
Note that we use AddressSanitizer for the benchmark builds of most fuzzers
(i.e. all of them support it) so that it will be easier to add support for
measuring performance based on crashes.

### Coverage builds

Running coverage builds does not require any dependencies that aren't available
on the dispatcher image. One reason for this is because OSS-Fuzz only allows
projects (which are used as benchmarks) to install dependencies in the docker
container they use for building, not the one they use for fuzzing. Therefore,
the consumer of coverage builds, the measurer, doesn't actually use the images
from coverage builds, it simply runs the binaries directly on the dispatcher.

## Scheduler

Once the builder has finished, the dispatcher starts the scheduler. The
scheduler is responsible for starting and stopping trial runners, which are
instances on Google Compute Engine. The scheduler will continuously try to
create instances for trials that haven't run yet. This means that if an
experiment requires too many resources from Google Cloud to complete at once, it
can still be run anyway after some resources are freed up by trials that have
stopped. The scheduler stops trials after they have run for the amount of time
specified when starting the experiment. The scheduler stops running after all
trials finish running.

## Trial runners

Trial runners are compute engine instances that fuzz benchmarks. They start by
pulling the docker images that were produced by the [builder](/#Builder) and
uploaded to the container registry. Then, from within the container, they run
[runner.py](https://github.com/google/fuzzbench/blob/master/experiment/runner.py)
which calls the `fuzz` function from the `fuzzer.py` file for the specified
fuzzer
([example](https://github.com/google/fuzzbench/blob/master/fuzzers/fairfuzz/fuzzer.py)).
The runner will also periodically archive the current `output_corpus` and sync
it to [Google Cloud Storage](https://cloud.google.com/storage) (this is
sometimes referred to as a "corpus snapshot"). The runner terminates when it has
run the `fuzz` function for the time specified for each trial when starting an
experiment.

## Measurer

The role of the
[measurer](https://github.com/google/fuzzbench/blob/master/experiment/measurer.py)
is to take the output of the trial runners and make it usable for generating
reports. To do this, the measurer downloads coverage builds for each benchmark
and then continuously downloads corpus snapshots, measures their coverage, and
saves the result to the database, a [PostgreSQL](https://www.postgresql.org/)
instance running on [Google Cloud SQL](https://cloud.google.com/sql). The
measurer terminates when there is no corpus snapshot for this experiment that
hasn't been measured. Because the measurer is run on the dispatcher instance, it
can't scale with the size of an experiment, so it can actually finish after the
experiment is done (usually a few hours after the end of an experiment). The
dispatcher instance terminates after the measurer terminates itself.

## Reporter

The role of the reporter is to convert coverage (and other data in the future)
data output by the measurer into a human consumable report. It runs continuously
in a loop while the dispatcher is alive, consuming the coverage data from the
SQL database and then outputting an HTML report which it saves to a Google Cloud
Storage bucket (which you can access by going to
[fuzzbench.com/reports/](https://fuzzbench.com/reports/)).
