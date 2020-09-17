---
layout: default
title: The FuzzBench Service
parent: Internal Documentation
nav_order: 1
permalink: /internal-documentation/service/
---

# The FuzzBench service
{: .no_toc}

**Note:** This document and most of the `service/` directory is only intended
for use by FuzzBench maintainers. It will contain hardcoded values and
references to things that don't make sense for other users.

- TOC
{:toc}

## Overview

This document discusses the FuzzBench service. The service works as follows:
When a user wants a new experiment they add the experiment to
`experiment-requests.yaml`. Twice a day at 6 AM PT (13:00 UTC) and 6 PM PT
(01:00 UTC) a cron job on the `service` instance will execute the script
`run.bash`. `run.bash` will clone FuzzBench and then execute
`automatic_run_experiment.py` which starts newly requested experiments.

## Setting up an instance to run an experiment

This shouldn't be necessary, but here are instructions in case the current
instance is lost.
1. Run `setup.bash`. This will build and install a supported Python version,
   download the `cloud_sql_proxy` and run it so that we have a connection to the
   db.

1. Install the cron job. An example you can use is in the
   [crontab file](https://github.com/google/fuzzbench/tree/master/service/crontab).
   Note that you must fill in `POSTGRES_PASSWORD` and `$HOME`.

1. Verify that the service is running. One way you can debug this is by looking
   at the stdout/stderr of `run.bash` which is saved in
   `/tmp/fuzzbench-service.log`. If something isn't working you should probably
   verify that `run.bash` works on its own. Note that `run.bash` is executed
   from a checkout of FuzzBench that isn't automatically updated. So if you need
   to update you must do so with `git pull --rebase`.

## Automatic merging

Experiments that are run using the service will be marked as nonprivate and on
completion automatically merge using clobbering.
