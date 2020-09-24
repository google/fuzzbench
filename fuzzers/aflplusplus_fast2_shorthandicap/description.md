# aflplusplus

AFL++ fuzzer instance that has the following config active for all benchmarks:
  - PCGUARD instrumentation 
  - cmplog feature
  - dict2file feature
  - new "fast2" power schedule
  - fastcount patch
  - substantially less handicap bonus energy for seeds added in late cycles
  - persistent mode + shared memory test cases

Repository: [https://github.com/AFLplusplus/AFLplusplus/](https://github.com/AFLplusplus/AFLplusplus/)

[builder.Dockerfile](builder.Dockerfile)
[fuzzer.py](fuzzer.py)
[runner.Dockerfile](runner.Dockerfile)
