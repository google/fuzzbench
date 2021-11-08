# aflplusplus_qemu

AFL++ fuzzer instance for binary-only fuzzing with qemu_mode.
The following config active for all benchmarks:
  - qemu_mode with:
    - entrypoint set to afl_qemu_driver_stdin_input
    - persisten mode set to afl_qemu_driver_stdin_input
    - cmplog

Repository: [https://github.com/AFLplusplus/AFLplusplus/](https://github.com/AFLplusplus/AFLplusplus/)

[builder.Dockerfile](builder.Dockerfile)
[fuzzer.py](fuzzer.py)
[runner.Dockerfile](runner.Dockerfile)
