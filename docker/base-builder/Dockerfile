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

# Don't install recommended packages since x11 seems to get
# recommended for some reason.
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    automake \
    git \
    libtool \
    subversion \
    unzip \
    wget

# Copy clang binaries and libs.
COPY --from=base-clang /usr/local/bin/clang* /usr/local/bin/
COPY --from=base-clang /usr/local/bin/llvm-* /usr/local/bin/
COPY --from=base-clang /usr/local/lib/clang /usr/local/lib/clang
COPY --from=base-clang /usr/local/lib/libc++*.a /usr/local/lib/
COPY --from=base-clang /usr/local/include/ /usr/local/include

ENV CC="clang"
ENV CXX="clang++"

ENV CFLAGS="-O3"
ENV CXXFLAGS="-O3 -stdlib=libc++"
