# aflplusplus

AFL++ fuzzer instance that has the following config active for all benchmarks:
  - PCGUARD instrumentation 
  - cmplog feature
  - dict2file feature
  - persistent mode + shared memory test cases
  - envs: AFL_FAST_CAL, AFL_DISABLE_TRIM, AFL_CMPLOG_ONLY_NEW, AFL_NO_SYNC
Defaults are active otherwise.

Repository: [https://github.com/AFLplusplus/AFLplusplus/](https://github.com/AFLplusplus/AFLplusplus/)

[builder.Dockerfile](builder.Dockerfile)
[fuzzer.py](fuzzer.py)
[runner.Dockerfile](runner.Dockerfile)
