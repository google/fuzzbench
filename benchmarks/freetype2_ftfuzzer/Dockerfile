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

FROM gcr.io/oss-fuzz-base/base-builder

# Install necessary dependencies
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y \
    make \
    autoconf \
    libtool \
    wget

# Clone necessary repositories
RUN git clone git://git.sv.nongnu.org/freetype/freetype2.git $SRC/freetype2
RUN git clone https://github.com/unicode-org/text-rendering-tests.git $SRC/TRT
RUN wget https://github.com/libarchive/libarchive/releases/download/v3.4.3/libarchive-3.4.3.tar.xz -P $SRC/
RUN wget https://raw.githubusercontent.com/ardier/fuzzbench/minimized-subsumed-mutants-benchmark-with-seeds/benchmarks/freetype2_ftfuzzer_libafl/seeds.tar -O $SRC/seeds.tar && \
    mkdir -p $SRC/seeds && \
    tar -xvf $SRC/seeds.tar -C $SRC/seeds

# Copy all files into $SRC directory
COPY * $SRC/

