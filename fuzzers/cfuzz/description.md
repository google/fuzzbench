# cfuzz

cfuzz fuzzer instance that has the following config active for all benchmarks:
  - PCGUARD instrumentation 
  - cmplog feature
  - dict2file feature
  - "exploit" power schedule
  - persistent mode + shared memory test cases

Repository: [https://github.com/zerokay/cfuzz/](https://github.com/zerokay/cfuzz/)

[builder.Dockerfile](builder.Dockerfile)
[fuzzer.py](fuzzer.py)
[runner.Dockerfile](runner.Dockerfile)
