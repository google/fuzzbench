# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

FROM gcr.io/fuzzbench/base-image

RUN apt update && apt install -y lsb-release wget software-properties-common gnupg
RUN wget https://apt.llvm.org/llvm.sh && chmod +x llvm.sh && ./llvm.sh 12
RUN apt install -y unzip git gdb joe libz3-dev libgoogle-perftools-dev \
    libc++-12-dev libc++abi-12-dev libunwind-12 python-is-python3

ENV LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/out"
#ENV AFL_MAP_SIZE=900000
#ENV AFL_QUIET=1
ENV PATH="$PATH:/out"
ENV AFL_SKIP_CPUFREQ=1
#ENV AFL_NO_UI=1
#ENV AFL_NO_AFFINITY=1
ENV AFL_SKIP_CRASHES=1
ENV AFL_TESTCACHE_SIZE=2
ENV AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1
