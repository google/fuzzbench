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

ARG parent_image=gcr.io/fuzzbench/base-builder
FROM $parent_image

# Download and compile AFL v2.56b.
# Set AFL_NO_X86 to skip flaky tests.
RUN apt-get update && \
    apt-get install -y wget lcov

RUN git clone https://github.com/vanhauser-thc/afl-cov /afl && \
    cd /afl && \
    clang++ -O2 -stdlib=libc++ -std=c++11 -c /afl/libfuzzer_driver.cpp && \
    ar r /libAFL.a *.o
