# aflplusplusplus

AFL++ fuzzer instance that has the following config active for all benchmarks:
  - PCGUARD instrumentation 
  - cmplog feature
  - autodictionary
  - "fast" power schedule
  - persistent mode + shared memory test cases

And as a special feature for SBFT23: autotoken, an implementation to create
grammar for targets with textual inputs (e.g. json, xml), without knowing
their structure.

Repository: [https://github.com/AFLplusplus/AFLplusplus/](https://github.com/AFLplusplus/AFLplusplus/)

[builder.Dockerfile](builder.Dockerfile)
[fuzzer.py](fuzzer.py)
[runner.Dockerfile](runner.Dockerfile)
