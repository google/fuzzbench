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

ARG parent_image
FROM $parent_image

# Install libstdc++ to use llvm_mode.
RUN apt-get update && \
    apt-get install -y wget libstdc++-5-dev libtool-bin automake flex bison \
                       libglib2.0-dev libpixman-1-dev python3-setuptools unzip \
                       apt-utils apt-transport-https ca-certificates joe

# Download libafl
RUN git clone https://github.com/AFLplusplus/libafl /libafl && \
    cd /libafl && \
    git checkout 77e0be218a8843c7af6c6d35eb4b94b4cc12b289

# Compile libafl
RUN cd /libafl && unset CFLAGS && unset CXXFLAGS && \
    export CC=clang && export CXX=clang++ && \
    export LIBAFL_EDGES_MAP_SIZE=2621440 && \
    cd ./fuzzers/fuzzbench && cargo build --release

RUN wget https://gist.githubusercontent.com/andreafioraldi/e5f60d68c98b31665a274207cfd05541/raw/4da351a321f1408df566a9cf2ce7cde6eeab3904/empty_fuzzer_lib.c -O /empty_fuzzer_lib.c && \
    clang -c /empty_fuzzer_lib.c && \
    ar r /emptylib.a *.o
