# Experiment data analysis and reporting library

## Concepts

The library makes extensive use of Pandas data frames representing measurements.
The data frames typically have the following columns:

`benchmark, fuzzer, trial_id, time, edges_covered, ...`

We can differentiate three types of data frames described below.

### Experiment

An "experiment" represents a data frame that includes measurements on multiple benchmarks, multiple fuzzers, and multiple trials.

Functions taking experiment data have parameter name `experiment_df`.

### Benchmark

A "benchmark" represents a data frame that includes measurements on _single_ benchmark. (It can still have multiple fuzzers, and multiple trials.)

Functions taking benchmark data have parameter name `benchmark_df`.

### Snapshot

To compare fuzzers, e.g., based on the coverage they reached, we need to select a point in time along the course of the (typically 24 hours long) experiment, to take the coverage measurements from.
We call this time the _snapshot time_.
Typically we are interested in the maximum coverage reachable by a fuzzer, in which case the best is to pick the latest possible time.
The measurements taken at that selected snapshot time will be the input of most of our analysis (e.g., for ranking, statistical tests).
Therefore a "snapshot" represents a data frame where all `time` values are the same for a given `benchmark`.

Functions taking a snapshot of a benchmark have parameter name `benchmark_snapshot_df`.
Functions taking the snapshot of all benchmarks in an experiment have parameter name `experiment_snapshot_df`.
