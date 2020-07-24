# Copyright 2016 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
################################################################################

FROM gcr.io/oss-fuzz-base/base-builder@sha256:dc0a0e4327c53b000c63837c5ea8d5e8f18fb0fb2a38abd4249dedca39ed0a1f

# Curl will be checked out to the commit hash specified in benchmark.yaml.
RUN git clone --depth 1 https://github.com/curl/curl.git /src/curl
RUN git clone https://github.com/curl/curl-fuzzer.git /src/curl_fuzzer
RUN git -C /src/curl_fuzzer checkout -f 82eb95b410cc84579b8f9d663f2a7e38f3bdb41f

# Use curl-fuzzer's scripts to get latest dependencies.
RUN $SRC/curl_fuzzer/scripts/ossfuzzdeps.sh

WORKDIR $SRC/curl_fuzzer
COPY build.sh $SRC/
