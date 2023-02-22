# hastefuzz

AFL++ fuzzer instance that has the following config active for all benchmarks:
  - PCGUARD instrumentation 
  - cmplog feature
  - dict2file feature
  - "fast" power schedule
  - persistent mode + shared memory test cases
  - haste mode

Repository: [https://github.com/AAArdu/hastefuzz](https://github.com/AAArdu/hastefuzz)

[builder.Dockerfile](builder.Dockerfile)
[fuzzer.py](fuzzer.py)
[runner.Dockerfile](runner.Dockerfile)
