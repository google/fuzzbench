# libaflfuzzer

A new fuzzer loosely based on libfuzzer, afl and afl++ concepts.
Very WIP and still missing a lot of features, e.g. no dictionary support,
no CPU binding, no advanced havoc mode, no different schedules, etc.

Threaded in-memory fuzzing.

Repository: [https://github.com/AFLplusplus/libAFL/](https://github.com/AFLplusplus/libAFL/)

[builder.Dockerfile](builder.Dockerfile)
[fuzzer.py](fuzzer.py)
[runner.Dockerfile](runner.Dockerfile)
