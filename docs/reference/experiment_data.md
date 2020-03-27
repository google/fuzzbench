---
layout: default
title: Experiment data
parent: Reference
nav_order: 5
permalink: /reference/experiment-data/
---

# Experiment data

This page describes how to obtain the raw data produced during an experiment.
This includes corpora, crashes and logs from fuzzers.
It does not include the metrics used to generate a report, that data is linked
to in the report itself.

This page is written for users of the FuzzBench service. The same concepts apply
to users running fuzzbench on their own however, the Google Cloud Storage buckets
will be different.

## Getting the data

[commondatastorage.googleapis.com/fuzzbench-data/](http://commondatastorage.googleapis.com/fuzzbench-data/)
provides an XML file listing every from every experiment that is available for
download. It isn't very usable for use in a browser but can probably be used by
any S3 compatible tool.

We use gsutil for obtaining this data. Follow [these instructions to install
gsutil](https://cloud.google.com/storage/docs/gsutil_install#install).

With gsutil you can do `gsutil ls gs://experiment-data/$EXPERIMENT_NAME/` list
files in cloud storage directories for your project and you can use `gsutil cp`
to copy them.

## Data layout

Let's see what the layout of this data directory looks like:

```
gs://$EXPERIMENT_NAME
│
└───build-logs
│       build-log-1.txt
│       ...
│
└───coverage-binaries
│       coverage-build-$BENCHMARK.tar.gz
│       ...
│
└───experiment-folders
│   │
│   └───$BENCHMARK-$FUZZER
│   │   │
│   │   └───trial-$TRIAL_NUM
│   │   │   │
│   │   │   └───corpus
│   │   │   │       corpus-archive-0001.tar.gz
│   │   │   │       ...
│   │   │   │
│   │   │   └───crashes
│   │   │   │       crashes-0001.tar.gz
│   │   │   │       ...
│   │   │   │
│   │   │   └─results
│   │   │          fuzzer-log.txt
│   │   │          unchanged-cycles
│   │   │
│   │   └─...
│   │
│   └─ ... 
│
└───input # Contains source code and config files used to run experiment.
```

### Corpus archive and unchanged-cycles

A trial is a run of a specific fuzzer on a specific benchmark.
For each trial, FuzzBench archives the `output_directory` used in `fuzzer.py`
every 15 minutes, this is sometimes referred to as a "snapshot" (or "cycle"). As an
optimization, if the directory hasn't changed since the last cycle, the archiving step
is skipped and the cycle number is added to `unchanged-cycles`. For some fuzzers
like AFL, we ignore frequently changing non-corpus files like `fuzzer_stats`
when determining if this cycle has changes. Because `fuzzer_stats` is included
in the archive, you can obtain stats for an AFL-based fuzzer using the last
archive in a trial.

### Crashes

Though FuzzBench doesn't use crashes for measuring performance, it does save them.
When FuzzBench measures the coverage of a corpus snapshot, if it encounters any
crashes it adds them to the crashes archive for that cycle.

### fuzzer-log.txt

The stdout and stderr from running a fuzzer.
