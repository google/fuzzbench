---
layout: default
title: Adding a new benchmark
parent: Developing FuzzBench
nav_order: 1
permalink: /developing-fuzzbench/adding-a-new-benchmark/
---

# Adding a new benchmark
{: .no_toc}

This page explains how to add a new benchmark to FuzzBench and test it.

- TOC
{:toc}

## OSS-Fuzz benchmarks vs Standard benchmarks

FuzzBench supports two methods of integrating benchmarks: OSS-Fuzz and standard.
The OSS-Fuzz method makes it easy to integrate a fuzz target from an OSS-Fuzz
project as a benchmark. With the "standard" method, instead of using our helper
script to copy the project's `build.sh` and `Dockerfile` from the OSS-Fuzz
repo, you must create these yourself.

## OSS-Fuzz benchmarks

You can use most existing OSS-Fuzz projects a benchmark. First decide which project
and fuzz target you want to use as a benchmark. Next, find out the commit at which
you want to use the project for the benchmark. Finally, find out the date and time
(UTC) of that commit in ISO format. You can get the date and time from the project
(benchmark) repo with this command:
```shell
git --no-pager log -1 $COMMIT_HASH --format=%cd --date=iso-strict
```

Once you have this information, run
`benchmarks/oss_fuzz_benchmark_integration.py` to copy the necessary integration
files, like so:

```shell
PYTHONPATH=. python3 benchmarks/oss_fuzz_benchmark_integration.py -p $PROJECT
    -f $FUZZ_TARGET -c $COMMIT_HASH -d $COMMIT_DATE
```
Example :
```shell
PYTHONPATH=. python3 benchmarks/oss_fuzz_benchmark_integration.py -p bloaty
    -f fuzz_target -c f572d396fae9206628714fb2ce00f72e94f2258f -d 2019-10-19T09:07:25+01:00
```

The script should create the benchmark directory in
`benchmarks/$PROJECT_$FUZZ_TARGET` (unless you specify the name manually) with
all the files needed to build the benchmark. You should remove unnecessary files
such as fuzz targets which are not used for the benchmark. The `*.options` files are
usually unused, thus it is recommended to remove them along with the commands that
copy them to `$SRC` or `$OUT`. Further, the `build.sh` file may also need to be
modified accordingly, so as to build only the required fuzz target.

Add the files in the benchmark directory to git (and then commit them):

```shell
git add benchmarks/$BENCHMARK_NAME/*
```

## Standard benchmarks: Create benchmark files

This process is very similar to adding a project to
[OSS-Fuzz](https://google.github.io/oss-fuzz/getting-started/new-project-guide/).
Note that this is not the same as integrating an OSS-Fuzz benchmark, since the
integration work has already been done in the OSS-Fuzz repo.
At a high level it involves:
1. [Creating a directory for your benchmark](#create-benchmark-directory).
2. [Creating a fuzz target for your benchmark](#defining-a-fuzz-target).
3. [Creating a Dockerfile](#dockerfile) and a [build.sh](#buildsh) to build your
   benchmark for fuzzing.
4. [Creating a `benchmark.yaml` file](#benchmarkyaml) to define important
   details about your benchmark.

### Create benchmark directory

Create a subdirectory under the root `benchmarks` directory. The name of this
subdirectory will be the name FuzzBench uses for the benchmark. The benchmark
name can contain alphanumeric characters, dots, hyphens and underscores.

```bash
cd benchmarks
export BENCHMARK_NAME=<your_benchmark_name>
mkdir $BENCHMARK_NAME
```

### Defining a fuzz target

Benchmarks in OSS-Fuzz consist of open source code and [a libFuzzer compatible
entrypoint](https://llvm.org/docs/LibFuzzer.html#fuzz-target) into the targeted
code that fuzzers such as AFL, libFuzzer and honggfuzz send data to fuzz.
This section describes how to create a file that defines this entrypoint.
This file  should define a
`LLVMFuzzerTestOneInput` function that accepts an array of bytes and the
length of this array. This function should then pass those bytes to an API
in the project/program that we want to fuzz.

```c
extern "C" int LLVMFuzzerTestOneInput(const uint8_t *Data, size_t Size) {
  DoSomethingInterestingWithMyAPI(Data, Size);
  return 0;  // Non-zero return values are reserved for future use.
}
```
For example, if the project we are fuzzing is a JSON parsing library, our
`LLVMFuzzerTestOneInput` could pass the data from the fuzzer to a function in
the library that parses JSON.

Example: [libxml2](https://github.com/google/fuzzbench/blob/master/benchmarks/libxml2-v2.9.2/target.cc).

### build.sh

This file builds the fuzz target for your benchmark. It should use the
environment variables `CC`, `CXX`, `CFLAGS`, `CXXFLAGS` `$OUT` and the fuzzer
library.
`FUZZER_LIB` ([explanation]({{ site.baseurl }}/getting-started/adding-a-new-fuzzer/#what-is-fuzzer_lib))
for this. These environment variables will be defined when `build.sh` runs
By linking your fuzz target with the `FUZZER_LIB` and the project under test,
you will produce a binary that can be fuzzed by the FuzzBench fuzzers. This is
called the fuzz target binary. `FUZZER_LIB` is specific to each fuzzer, its
primary purpose is taking data from the fuzzer and passing it to your
benchmark's `LLVMFuzzerTestOneInput` function.

Once the build is finished, copy the fuzz target binary, any library
dependencies (and optionally the seeds directory and the dictionary)
into the output directory (`$OUT`).
**NOTE**: Only build artifacts added in `$OUT` directory are available when
running the fuzzer. You should not have any dependencies outside of `$OUT`.

```bash
#!/bin/bash -ex

# Build project.
./autogen.sh && ./configure && make -j

# Build fuzz target in $OUT directory.
export FUZZ_TARGET=fuzz_target
$CXX $CXXFLAGS ${SCRIPT_DIR}/fuzz_target.cc \
    -I BUILD/path/to/include/dir BUILD/path/to/project-lib.a \
    $FUZZER_LIB \
    -o $OUT/$FUZZ_TARGET

# Optional: Copy seeds directory to $OUT directory.
cp -r seeds $OUT/

# Optional: Copy dictionary to $OUT directory.
cp $FUZZ_TARGET.dict $OUT/
```

Example: [libxml2](https://github.com/google/fuzzbench/blob/master/benchmarks/libxml2-v2.9.2/build.sh).

#### `seeds` directory (optional)

This directory should contain a set of test input files for the fuzz target that
provide good code coverage to start from. This should be copied to `$OUT/seeds`

Example: [libpng-1.2.56](https://github.com/google/fuzzbench/blob/master/benchmarks/libpng-1.2.56/seeds).


#### Dictionary file (optional)

In the `$OUT` directory, you can define a file that will be used by fuzzers as a
[dictionary](https://llvm.org/docs/LibFuzzer.html#id31). This file have the same
name as the fuzz target binary followed by a `.dict` file extension. For example
if your fuzz target binary is `$OUT/fuzz-target` the dictionary should be
`$OUT/fuzz-target.dict`.

### Dockerfile

This file defines the steps to build the docker image for your benchmark.
It should inherit from `gcr.io/oss-fuzz-base/base-builder` and do any one-time
setup needed to build your benchmark, but should not actually build the
benchmark itself. It also should copy any files from the benchmark directory
into the image that will be needed to build the benchmark.

```dockerfile
FROM gcr.io/oss-fuzz-base/base-builder

RUN apt-get update && \
    apt-get install -y \
    make \
    <any-other-packages-needed-to-build-the-benchmark>

COPY build.sh fuzz-target.dict $SRC/
ADD seeds $SRC/seeds
```

Example: [libxml2](https://github.com/google/fuzzbench/blob/master/benchmarks/libxml2-v2.9.2/Dockerfile).

### benchmark.yaml

Define the name of your fuzz target binary and the project that is fuzzed as
part of the benchmark like so:

```yaml
fuzz_target: fuzz-target
project: $PROJECT_NAME
```

Example: [libxml2](https://github.com/google/fuzzbench/blob/master/benchmarks/libxml2-v2.9.2/benchmark.yaml).

## Testing it out

Once you integrated a benchmark, you should test that it builds and runs
successfully with at least one fuzzer (e.g. afl):

```shell
export FUZZER_NAME=afl
export BENCHMARK_NAME=libpng-1.2.56

make build-$FUZZER_NAME-$BENCHMARK_NAME

# This command will fuzz forever. Press Ctrl-C to stop it.
make run-$FUZZER_NAME-$BENCHMARK_NAME
```

## Submitting the benchmark in a pull request

If everything works, submit the integration in a
[GitHub pull request](https://help.github.com/en/github/collaborating-with-issues-and-pull-requests/creating-a-pull-request).

## Overview of how builds work in FuzzBench

We don't think most end users need to know how this process works. But we
describe it anyway for edge cases where this knowledge may help. Note that this
process may change as it is fairly complex since it needs to ensure that the
resulting docker images can run FuzzBench, build arbitrary fuzzers and build
arbitrary benchmarks for their use, while trying to hide some implementation
details from fuzzers and benchmarks.

### Building benchmarks and fuzzers.

Building benchmarks and fuzzers entails the following process:

1. The benchmark image is built. This image is defined by
   `benchmarks/$BENCHMARK/Dockerfile`. It inherits from
   `gcr.io/oss-fuzz-base/base-builder` which provides clang and other things
   needed by benchmarks (particular OSS-Fuzz benchmarks to build). Standard
   benchmarks (usually) inherit from the latest version of `base-builder`
   while OSS-Fuzz benchmarks (usually) inherit from the specific version of
   `base-builder` that was used to build the version of the project's source
   (commit) that the benchmark uses. This is to ensure that builds of these
   benchmarks just work and don't break when `base-builder` is updated to use a
   new version of clang. Note that pinning some benchmarks to specific versions
   of clang is a bit ugly and this behavior may change in the future.

1. The fuzzer builder image is built. This image is defined by
   `fuzzers/$FUZZER/builder.Dockerfile`. This dockerfile will inherit from
   a parent image that is provided to it at buildtime (using the docker
   variable: `parent_image`). The parent image provided is the benchmark docker
   image from the previous step. The fuzzer builder image builds the fuzzer sets
   up anything the fuzzer needs to build the benchmark (such as `FUZZER_LIB`).

1. The benchmark builder image is built. This image is defined by
   `docker/benchmark-builder/Dockerfile`. This inherits from the fuzzer builder
   image. This is the first image in this build process that is defined by the
   main FuzzBench code (e.g. not fuzzers, benchmarks, or OSS-Fuzz). Its first
   function is to copy the FuzzBench code and install packages needed to run
   FuzzBench like Python3.7 For benchmarks that define a `commit` in their
   `benchmark.yaml` (i.e. OSS-Fuzz benchmarks) the build process for this image
   checks out the source code of that project at the specified commit. Then the
   process defines the environment variables `CC`, `CXX`, `CXXFLAGS`, `CFLAGS`
   and `OUT`. It then calls the `build` function from the fuzzer's `fuzzer.py`
   file. `build` can change these environment variables as needed and then calls
   `build_benchmark` from `fuzzers/utils.py`. `build_benchmark` invokes the
   `build.sh` file of the benchmark building it with environment variables
   provided by `fuzzer.py` or the benchmark builder image. `build` then copies
   build of the `fuzzer` (e.g. `afl-fuzz`) to `$OUT` (one reason why we do this
   here instead of when building the fuzzer is because the `build.sh` can
   overwrite it, in the future we will probably ensure that the build processes
   for the benchmark and the fuzzer don't interfere). In some cases, such as
   QSYM (which is no longer a supported fuzzer for other reasons), `build` can
   reset `OUT` so that it can build the benchmark twice since some fuzzers may
   need two different builds of the same benchmark.

1. Runners: TODO
