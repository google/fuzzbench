---
layout: default
title: Adding a new fuzzer
parent: Getting started
nav_order: 3
permalink: /getting-started/adding-a-new-fuzzer/
---

# Adding a new fuzzer
{: .no_toc}

This page explains how to add your fuzzer so it can be benchmarked using
FuzzBench. Before you begin make sure you've followed the
[prerequisites]({{ site.baseurl }}/getting-started/prerequisites/) section.

- TOC
{:toc}

## Create fuzzer directory

Create a subdirectory under the root `fuzzers` directory. The name of this
subdirectory will be the name FuzzBench uses for your fuzzer. The fuzzer name
can contain alphanumeric characters and underscores and must be a valid python
module.

```bash
export FUZZER_NAME=<your_fuzzer_name>
cd fuzzers
mkdir $FUZZER_NAME
```

You can verify the name of your fuzzer is valid by running `make presubmit`
from the root of the project.

## Create fuzzer files

### builder.Dockerfile

This file defines the image that will build your fuzzer and benchmarks for use
with your fuzzer. For most projects, this will look like:

```dockerfile
ARG parent_image
FROM $parent_image                         # Base builder image (Ubuntu 16.04, with latest Clang).

RUN apt-get update && \                    # Install any system dependencies to build your fuzzer.
    apt-get install -y pkg1 pkg2

RUN git clone <git_url> /fuzzer_src        # Clone your fuzzer's sources.

RUN cd /fuzzer_src && make                 # Build your fuzzer using its preferred build system.

# Build your `FUZZER_LIB`.
# See section below on "What is `FUZZER_LIB`?" for more details.
RUN git clone <git_url> /fuzzer_lib_src

RUN cd /fuzzer_lib_src && clang++ fuzzer_lib.o
```

Example: [afl](https://github.com/google/fuzzbench/blob/master/fuzzers/afl/builder.Dockerfile).

### runner.Dockerfile

This file defines the image that will be used to run benchmarks with your
fuzzer. Making this lightweight allows trial instances to be spun up fast.

```dockerfile
FROM gcr.io/fuzzbench/base-image           # Base image (Ubuntu 16.04).

RUN apt-get update && \                    # Install any runtime dependencies for your fuzzer.
    apt-get install pkg1 pkg2
```

Example: [honggfuzz](https://github.com/google/fuzzbench/blob/master/fuzzers/honggfuzz/runner.Dockerfile).

As you can see by looking at the runner.Dockerfile of other projects, in most
cases only the `FROM` line is needed since most fuzzers do not have any special
runtime dependencies.

### fuzzer.py

This file specifies how to build and fuzz benchmarks using your fuzzer. We hope
to have accommodated most common use cases but please [file an issue](https://github.com/google/fuzzbench/issues/new) if
you're having trouble.

In your fuzzer directory, create a Python file named `fuzzer.py`. It must
contain two functions:
```python
def build():
```
A function that accepts no arguments and returns nothing. This function must do
two things:
1. Build the benchmark.
This is usually done by setting the necessary environment variables, including
`CFLAGS`, `CXXFLAGS`, `CC`, `CXX` and `FUZZER_LIB`. Note that `CFLAGS` and
`CXXFLAGS` should be appended to (using `utils.append_flags` functions) in most
cases, and not set directly (i.e. overwritten).
1. Copy everything your fuzzer needs to run to the `$OUT` directory.

```python
def fuzz(input_corpus, output_corpus, target_binary):
```
A function that accepts three arguments `input_corpus`, `output_corpus` and
`target_binary` and returns nothing. `fuzz` should use these arguments to
fuzz the `target_binary` using your fuzzer.

We have provided an example `fuzzer.py` with comments explaining the necessary
parts below:


```python
import os
import subprocess
import ...  # Import any other python libs you need.

# Helper library that contains important functions for building.
from fuzzers import utils

def build():
    """Build benchmark and copy fuzzer to $OUT."""
    flags = [
        # List of flags to append to CFLAGS, CXXFLAGS during
        # benchmark compilation.
    ]
    utils.append_flags('CFLAGS', flags)     # Adds flags to existing CFLAGS.
    utils.append_flags('CXXFLAGS', flags)   # Adds flags to existing CXXFLAGS.

    os.environ['CC'] = 'clang'              # C compiler.
    os.environ['CXX'] = 'clang++'           # C++ compiler.

    os.environ['FUZZER_LIB'] = 'fuzzer.a'   # Path to your compiled fuzzer lib.

    # Helper function that actually builds benchmarks using the environment you
    # have prepared.
    utils.build_benchmark()

    # You should copy any fuzzer binaries that you need at runtime to the
    # $OUT directory. E.g. for AFL:
    # shutil.copy('/afl/afl-fuzz', os.environ['OUT'])


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer.

    Arguments:
      input_corpus: Directory containing the initial seed corpus for
                    the benchmark.
      output_corpus: Output directory to place the newly generated corpus
                     from fuzzer run.
      target_binary: Absolute path to the fuzz target binary.
    """
    # Run your fuzzer on the benchmark.
    subprocess.call([
        your_fuzzer,
        '<flag-for-input-corpus>',
        input_corpus,
        '<flag for-output-corpus',
        output_corpus,
        '<other command-line options>',
        target_binary,
    ])
```

Example: [afl](https://github.com/google/fuzzbench/blob/master/fuzzers/afl/fuzzer.py).

Environment variables `FUZZER` and `BENCHMARK` are available to use during
execution of `build()` and `fuzz()` functions.

### What is `FUZZER_LIB`?

`FUZZER_LIB` is a library that gets linked against the benchmark which allows
your fuzzer to fuzz the benchmark.
For fuzzers like libFuzzer which run entirely in process, `FUZZER_LIB` is the
fuzzer itself.
For out-of-process fuzzers like AFL, `FUZZER_LIB` is a shim that allows them to
fuzz our benchmarks which have libFuzzer harnesses. In a libFuzzer harness:
fuzzer data is passed to targeted code through a
function called `LLVMFuzzerTestOneInput`:

```c
int LLVMFuzzerTestOneInput(const uint8_t *Data, size_t Size);
```
Therefore, AFL's shim takes data from AFL and passes it to
`LLVMFuzzerTestOneInput`.

If, like AFL, your fuzzer has a [persistent mode](https://lcamtuf.blogspot.com/2015/06/new-in-afl-persistent-mode.html),
your `FUZZER_LIB` should be a library that will call `LLVMFuzzerTestOneInput`
in a loop during fuzzing.
For example, in [afl's builder.Dockerfile](https://github.com/google/fuzzbench/blob/master/fuzzers/afl/builder.Dockerfile)
you can see how [afl_driver.cpp](https://github.com/llvm/llvm-project/blob/main/compiler-rt/lib/fuzzer/afl/afl_driver.cpp#L223-L276)
is built. In
[afl's fuzzer.py](https://github.com/google/fuzzbench/blob/master/fuzzers/afl/fuzzer.py)
this gets used as the `FUZZER_LIB`.

If your fuzzer does not support persistent mode, you can use the
[StandAloneFuzzTargetMain.cpp](https://github.com/llvm/llvm-project/blob/main/compiler-rt/lib/fuzzer/standalone/StandaloneFuzzTargetMain.c)
as your `FUZZER_LIB`. This file takes files as arguments, reads them, and
invokes `LLVMFuzzerTestOneInput` using their data as input
(See [Eclipser](https://github.com/google/fuzzbench/blob/master/fuzzers/eclipser/builder.Dockerfile)
for an example of this). This can be used for a fuzzer that must restart the
target after executing each input.

### Reusing existing integrations

Most fuzzers, such as FairFuzz are based off other fuzzers such as AFL.
In many cases such as these, the derivative fuzzer can simply reuse the
original's integration. For example, FairFuzz's
[fuzzer.py](https://github.com/google/fuzzbench/blob/master/fuzzers/fairfuzz/fuzzer.py)
imports AFL's `build` and `fuzz` functions and calls them from its own.
And its [builder.Dockerfile](https://github.com/google/fuzzbench/blob/master/fuzzers/fairfuzz/builder.Dockerfile)
is essentially a copy of AFL's [builder.Dockerfile](https://github.com/google/fuzzbench/blob/master/fuzzers/AFL/builder.Dockerfile)
that simply clones FairFuzz from a different source (Dockerfile functionality
should be copied to be reused, inheriting using `FROM` can't be used for this
purpose).

In the case of AFL, we have tried to write the `fuzzer.py` file to be modular
enough to support different use cases than needing the exact same binaries and
fuzzing invocation as AFL. Example:
[aflplusplus](https://github.com/google/fuzzbench/blob/master/fuzzers/aflplusplus/fuzzer.py).

## Testing it out

Once you've got a fuzzer integrated, you should test that it builds and runs
successfully:

* Build a specific benchmark:

```shell
export FUZZER_NAME=afl
export BENCHMARK_NAME=libpng-1.2.56
make build-$FUZZER_NAME-$BENCHMARK_NAME
```

* To debug a build:

```shell
make debug-builder-$FUZZER_NAME-$BENCHMARK_NAME
```
And then run `fuzzer_build` when you have a shell on the builder.

* Run the fuzzer in the docker image:

```shell
make run-$FUZZER_NAME-$BENCHMARK_NAME
```

* Or use a quicker test run mode:

```shell
make test-run-$FUZZER_NAME-$BENCHMARK_NAME
```

* Building all benchmarks for a fuzzer:

```shell
make build-$FUZZER_NAME-all
```

*Tips*:
* To debug fuzzer run-time issues, you can either:

  * Start a new shell and run fuzzer there:

    ```shell
    make debug-$FUZZER_NAME-$BENCHMARK_NAME

    $ROOT_DIR/docker/benchmark-runner/startup-runner.sh
    ```

  * Or, debug an existing fuzzer run in the `make run-*` docker container:

    ```shell
    docker container ls
    docker exec -ti <container-id> /bin/bash

    # E.g. check corpus.
    ls /out/corpus
    ```

* To do builds in parallel, pass -j <number_of_parallel_jobs> to make:

  ```shell
  make -j6 build-$FUZZER_NAME-all
  ```

* Run `make format` to format your code.

* Run `make presubmit` to lint your code and ensure all tests are passing.

* Run `make clear-cache` to clear docker containers' caches. Next time you build
  a project, the container will be built from scratch.

## Blocklisting benchmarks

You should make sure that your fuzzer builds and runs successfully against all
benchmarks integrated in FuzzBench. This can be done locally using the
`make test-run-$FUZZER_NAME-$BENCHMARK_NAME` command OR you can upload the
fuzzer pull request and wait for the CI results.

There can be unavoidable cases where your fuzzer cannot work with a particular
benchmark. In those cases, you can add your fuzzer to the `unsupported_fuzzers`
attribute of the benchmark's `benchmark.yaml` file. Check out an example
[here](https://github.com/google/fuzzbench/blob/bd281252287ed8bdf6eef31fbd7ea268c1b17cc9/benchmarks/bloaty_fuzz_target/benchmark.yaml#L19).

## Requesting an experiment

The FuzzBench service automatically runs experiments that are requested by users
twice a day at 6:00 AM PT (13:00 UTC) and 6:00 PM PT (01:00 UTC). If you want
the FuzzBench service to run an experiment on specific fuzzers (such as the one
you are adding): add an experiment request to
[service/experiment-requests.yaml](https://github.com/google/fuzzbench/blob/master/service/experiment-requests.yaml).
`service/experiment-requests.yaml` explains how to do this.

At the end of the experiment, FuzzBench will generate a report comparing your
fuzzer to the latest versions of other fuzzers, so you only need to include
fuzzers that you've modified in a meaningful way (i.e. fuzzers whose results are
likely affected by your change).

This report, and a real-time report of your experiment can be viewed at
`https://www.fuzzbench.com/reports/experimental/$YOUR_EXPERIMENT_NAME` (remove
the `experimental/` directory in path if you are modifying or adding a
[core fuzzer](https://github.com/google/fuzzbench/blob/master/service/core-fuzzers.yaml)).
Note that real-time reports may not appear until a few hours after the
experiment starts since every fuzzer-benchmark pair in the experiment must build
in order for fuzzing to start.

## Submitting your integration

* Add your fuzzer to the list in `.github/workflows/fuzzers.yml` so that our
  continuous integration will test that your fuzzer can build and briefly run on
  all benchmarks once you've submitted a pull request.

* Submit the integration in a
[GitHub pull request](https://help.github.com/en/github/collaborating-with-issues-and-pull-requests/creating-a-pull-request).
