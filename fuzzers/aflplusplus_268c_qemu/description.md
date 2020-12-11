# aflplusplus_qemu

AFL++ fuzzer instance for binary-only fuzzing with qemu_mode.
The following config active for all benchmarks:
  - qemu_mode with:
    - laf-intel (integers and floats)
    - entrypoint set to LLVMFuzzerTestOneInput
    - persisten mode set to LLVMFuzzerTestOneInput
    - in-memory shared memory test cases 
  - "explore" power schedule

Repository: [https://github.com/AFLplusplus/AFLplusplus/](https://github.com/AFLplusplus/AFLplusplus/)

[builder.Dockerfile](builder.Dockerfile)
[fuzzer.py](fuzzer.py)
[runner.Dockerfile](runner.Dockerfile)
