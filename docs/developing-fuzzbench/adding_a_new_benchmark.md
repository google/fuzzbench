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

## Create benchmark directory

Create a subdirectory under the root `benchmarks` directory. The name of this
subdirectory will be the name FuzzBench uses for the benchmark. The benchmark
name can contain alphanumeric characters, dots, hyphens and underscores.

```bash
export BENCHMARK_NAME=<your_benchmark_name>
cd benchmarks
mkdir $BENCHMARK_NAME
```

## OSS-Fuzz benchmarks vs standard benchmarks

FuzzBench supports two kinds of benchmarks, OSS-Fuzz and standard.
OSS-Fuzz benchmarks are OSS-Fuzz projects that are built for use as benchmarks.
Standard benchmarks allow using arbitrary code as benchmarks and are thus more
powerful but also more work.

## OSS-Fuzz benchmarks

You can use most existing OSS-Fuzz projects a benchmark. First find out which
project you want to use as a benchmark, and which commit and fuzz target you
want to use. Then find out the date and time (UTC) of that commit and the path
to the project's repository in the OSS-Fuzz builder image (usually it is
/src/$PROJECT_NAME).

Once you have this information, run `oss_fuzz/benchmark_integration.py` to copy
the necessary integration files, like so:

```shell
PYTHONPATH=. python3 benchmark_integration.py -p $PROJECT -f $FUZZ_TARGET \
    -r $REPO_PATH -c $ COMMIT_HASH -d $COMMIT_DATE
```

The script should create the benchmark directory in
`benchmarks/$PROJECT_$FUZZ_TARGET` (unless you specify the name manually) with
all the files needed to build the benchmark.

Add the files in the directory to git (and then commit them):

```shell
git add benchmarks/$BENCHMARK/*
```

Test your integration:

```shell
export FUZZER_NAME=afl
export BENCHMARK_NAME=zlib_zlib_uncompress_fuzzer

make build-$FUZZER_NAME-$BENCHMARK_NAME
make run-$FUZZER_NAME-$BENCHMARK_NAME
```

Add your benchmark to the list of OSS-Fuzz benchmarks in
[test_fuzzer_benchmarks.py](https://github.com/google/fuzzbench/blob/master/.github/workflows/test_fuzzer_benchmarks.py)

This ensures that CI tests your benchmark with all fuzzers.

If everything works, submit the integration in a
[GitHub pull request](https://help.github.com/en/github/collaborating-with-issues-and-pull-requests/creating-a-pull-request).

### Standard benchmarks: Create benchmark files

### fuzz_target.cc

This file defines the entry point for fuzzing. It should define a
`LLVMFuzzerTestOneInput` function that accepts an array of bytes and does
something interesting with these bytes using the program API under test.

```c
extern "C" int LLVMFuzzerTestOneInput(const uint8_t *Data, size_t Size) {
  DoSomethingInterestingWithMyAPI(Data, Size);
  return 0;  // Non-zero return values are reserved for future use.
}
```

Example: [libxml2](https://github.com/google/fuzzbench/blob/master/benchmarks/libxml2-v2.9.2/target.cc).

### build.sh

This file builds the fuzz target for your benchmark, taking into account
the compiler options - `CC`, `CXX`, `CFLAGS`, `CXXFLAGS` and the fuzzer library
`FUZZER_LIB` ([explanation]({{ site.baseurl }}/getting-started/adding-a-new-fuzzer/#what-is-fuzzer_lib))
as input.

Once the build is finished, copy the fuzz target binary, any library
dependencies and the seeds directory into the output directory (`$OUT`).
**NOTE**: Only build artifacts added in `$OUT` directory are available when
running the fuzzer. You should not have any dependencies outside of `$OUT`.


```bash
#!/bin/bash -ex
. $(dirname $0)/../common.sh

build_project() {
  rm -rf BUILD
  cp -rf SRC BUILD
  (cd BUILD && ./autogen.sh && ./configure && make -j $JOBS)
}
get_git_revision <path-to-git-repo> <git-hash> SRC
build_project

# Build fuzz target in $OUT directory.
$CXX $CXXFLAGS ${SCRIPT_DIR}/fuzz_target.cc \
    -I BUILD/path/to/include/dir BUILD/path/to/project-lib.a \
    $FUZZER_LIB \
    -o $OUT/fuzz_target

# Optional. Copy seeds directory to $OUT directory.
cp -r $SCRIPT_DIR/seeds $OUT/
```

Example: [libxml2](https://github.com/google/fuzzbench/blob/master/benchmarks/libxml2-v2.9.2/build.sh).

### seeds directory (optional)

This directory should contain a set of test input files for the fuzz target that
provide good code coverage to start from. This should be copied to `$OUT/seeds`

Example: [libpng-1.2.56](https://github.com/google/fuzzbench/blob/master/benchmarks/libpng-1.2.56/seeds).

## Testing it out

Once you integrated a benchmark, you should test that it builds and runs
successfully with at least one fuzzer (e.g. afl):

```shell
export FUZZER_NAME=afl
export BENCHMARK_NAME=libpng-1.2.56

make build-$FUZZER_NAME-$BENCHMARK_NAME
make run-$FUZZER_NAME-$BENCHMARK_NAME
```
Finally, add your benchmark to the list of OSS-Fuzz benchmarks in
[test_fuzzer_benchmarks.py](https://github.com/google/fuzzbench/blob/master/.github/workflows/test_fuzzer_benchmarks.py)

This ensures that CI tests your benchmark with all fuzzers.

If everything works, submit the integration in a
[GitHub pull request](https://help.github.com/en/github/collaborating-with-issues-and-pull-requests/creating-a-pull-request).
