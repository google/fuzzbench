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

# Using multi-stage build to copy clang.
FROM gcr.io/oss-fuzz-base/base-clang AS base-clang

FROM gcr.io/fuzzbench/base-image

RUN apt-get update -y && apt-get install -y \
    autoconf-archive \
    automake \
    cmake \
    git \
    golang \
    libarchive-dev \
    libbfd-dev \
    libboost-dev \
    libbz2-dev \
    libcairo2-dev \
    libdbus-1-dev \
    libfreetype6-dev \
    libgcrypt20-dev \
    libglib2.0-dev \
    libgss-dev \
    liblzma-dev \
    libssl-dev \
    libtool \
    libunwind-dev \
    libxml2-dev \
    nasm \
    openssl \
    ragel \
    subversion \
    wget

# Copy clang binaries and libs.
COPY --from=base-clang /usr/local/bin/clang* /usr/local/bin/
COPY --from=base-clang /usr/local/bin/llvm-* /usr/local/bin/
COPY --from=base-clang /usr/local/lib/clang /usr/local/lib/clang
COPY --from=base-clang /usr/local/lib/libc++*.a /usr/local/lib/
COPY --from=base-clang /usr/local/include/ /usr/local/include

# Use libc++ thoughout the build.
ENV CXXFLAGS -stdlib=libc++