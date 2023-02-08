# Copyright 2020 Google LLC
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

FROM gcr.io/oss-fuzz-base/base-builder@sha256:87ca1e9e19235e731fac8de8d1892ebe8d55caf18e7aa131346fc582a2034fdd

RUN apt-get update && \
    apt-get install -y \
    make \
    automake \
    autoconf \
    libtool

RUN git clone https://github.com/google/brotli.git && \
    git -C brotli checkout 3a9032ba8733532a6cd6727970bade7f7c0e2f52

RUN git clone https://github.com/google/woff2.git

# Get seeds.
RUN git clone https://github.com/google/oss-fuzz.git && \
    git -C oss-fuzz checkout e8ffee4077b59e35824a2e97aa214ee95d39ed13 && \
    mkdir -p $OUT/seeds && \
    cp oss-fuzz/projects/woff2/corpus/* $OUT/seeds

COPY target.cc build.sh $SRC/

WORKDIR woff2
