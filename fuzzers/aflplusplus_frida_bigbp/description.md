# aflplusplus_qemu

AFL++ fuzzer instance for binary-only fuzzing with frida_mode.
The following config active for all benchmarks:
  - qemu_mode with:
    - entrypoint set to LLVMFuzzerTestOneInput
    - persisten mode set to LLVMFuzzerTestOneInput
    - shared memory testcases
    - cmplog

Repository: [https://github.com/AFLplusplus/AFLplusplus/](https://github.com/AFLplusplus/AFLplusplus/)

[builder.Dockerfile](builder.Dockerfile)
[fuzzer.py](fuzzer.py)
[runner.Dockerfile](runner.Dockerfile)
