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
subdirectory will be the name of the benchmark. The benchmark name can contain
alphanumeric characters, dots, hyphens and underscores.

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

## Using existing OSS-Fuzz projects

You can use any existing OSS-Fuzz project as a benchmark. You just need to
create a single file `oss-fuzz.yaml` in the benchmark directory.

```yaml
project: <project-name>
fuzz_target: <fuzz-target-name>
oss_fuzz_builder_hash: <sha>
```
* `project` should be a [valid OSS-Fuzz project](https://github.com/google/oss-fuzz/tree/master/projects).
* `fuzz_target` should be the name of a binary fuzz target from the project that we want to fuzz as the benchmark.
* `oss_fuzz_builder_hash` is a SHA256 hash of a docker image from
[gcr.io/fuzzbench/oss-fuzz](https://console.cloud.google.com/gcr/images/fuzzbench/GLOBAL/oss-fuzz?gcrImageListsize=30).
Unless you are a project maintainer, you cannot build these images yourself.
Therefore, let us know the benchmark you want incorporated and we will produce a
build that can be used here.
Example: [wireshark_fuzzshark_ip](https://github.com/google/fuzzbench/blob/master/benchmarks/wireshark_fuzzshark_ip/oss-fuzz.yaml).

### Standard Benchmarks: Create benchmark files

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
dependencies and seeds directory into the output directory (`$OUT`).
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

Example [libpng-1.2.56](https://github.com/google/fuzzbench/blob/master/benchmarks/libpng-1.2.56/seeds).

## Testing it out

Once you've got a benchmark integrated, you should test that it builds and runs
successfully with at least one fuzzer (e.g. afl):

```shell
export FUZZER_NAME=afl
export BENCHMARK_NAME=libpng-1.2.56

make build-$FUZZER_NAME-$BENCHMARK_NAME
make run-$FUZZER_NAME-$BENCHMARK_NAME
```

If everything works, submit the integration code via a GitHub pull request.
