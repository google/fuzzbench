# aflplusplus

AFL++ fuzzer instance that has the following config active for all benchmarks:
  - PCGUARD instrumentation 
  - cmplog feature
  - "fast" power schedule
  - persistent mode + shared memory test cases

Repository: [https://github.com/AFLplusplus/AFLplusplus/](https://github.com/AFLplusplus/AFLplusplus/)

[builder.Dockerfile](builder.Dockerfile)
[fuzzer.py](fuzzer.py)
[runner.Dockerfile](runner.Dockerfile)
