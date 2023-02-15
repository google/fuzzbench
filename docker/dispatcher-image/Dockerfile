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

FROM gcr.io/oss-fuzz-base/base-clang@sha256:05774d8e388cb4975662c8eb25217e38a799d720b622e5c5d8abb79a76b49e53 AS base-clang

FROM gcr.io/fuzzbench/base-image

ENV WORK /work
WORKDIR $WORK

# Install runtime dependencies for benchmarks, easy json parsing, and fuzzbench.
RUN apt-get update -y && apt-get install -y \
    jq \
    libglib2.0-0 \
    libxml2 \
    libarchive13 \
    libgss3 \
    libgl1

# Install docker cli.
RUN DOCKER_VERSION=18.09.7 && \
    curl -O https://download.docker.com/linux/static/stable/x86_64/docker-$DOCKER_VERSION.tgz && \
    tar -xvzf docker-$DOCKER_VERSION.tgz && \
    mv docker/docker /usr/bin/ && \
    rm -rf docker docker-$DOCKER_VERSION.tgz

# Install cloud sql proxy.
RUN curl https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 > \
    /usr/local/bin/cloud_sql_proxy
RUN chmod +x /usr/local/bin/cloud_sql_proxy

# Copy llvm-tool binaries needed for clang source-code based coverage and
# symbolization.
COPY --from=base-clang /usr/local/bin/llvm-cov /usr/local/bin/
COPY --from=base-clang /usr/local/bin/llvm-profdata /usr/local/bin/
COPY --from=base-clang /usr/local/bin/llvm-symbolizer /usr/local/bin/

COPY startup-dispatcher.sh $WORK/
