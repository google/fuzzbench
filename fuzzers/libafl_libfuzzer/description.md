# libafl_libfuzzer

`libafl_libfuzzer` is a libfuzzer shim which attempts to replicate as many of the features of libfuzzer as possible
without utilising any customisation from the compiler, making it compatible with all libfuzzer targets while also using
all the advanced features of libafl.

Repository: [LibAFL/libfuzzer](https://github.com/AFLplusplus/LibAFL/tree/libfuzzer)

[builder.Dockerfile](builder.Dockerfile)
[fuzzer.py](fuzzer.py)
[runner.Dockerfile](runner.Dockerfile)
