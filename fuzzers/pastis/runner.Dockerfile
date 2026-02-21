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

# NOTE Comiple Python again with `--enabled-shared`.

# Python 3.10.8 is not the default version in Ubuntu 20.04 (Focal Fossa).
ENV PYTHON_VERSION 3.10.8

RUN cd /tmp/ && \
    curl -O https://www.python.org/ftp/python/$PYTHON_VERSION/Python-$PYTHON_VERSION.tar.xz && \
    tar -xvf Python-$PYTHON_VERSION.tar.xz > /dev/null && \
    cd Python-$PYTHON_VERSION && \
    ./configure \
        --enable-loadable-sqlite-extensions \
        --enable-optimizations \
        --enable-shared \
        > /dev/null && \
    make -j install > /dev/null && \
    rm -r /tmp/Python-$PYTHON_VERSION.tar.xz /tmp/Python-$PYTHON_VERSION

#
# Pastis.
#

# Install dependencies.
RUN DEBIAN_FRONTEND="noninteractive" \
    apt-get install -y --no-install-suggests --no-install-recommends \
        libmagic-dev

RUN pip install pastis-framework

#
# AFLplusplus
#

# This makes interactive docker runs painless:
ENV LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/out"
#ENV AFL_MAP_SIZE=2621440
ENV PATH="$PATH:/out"
ENV AFL_SKIP_CPUFREQ=1
ENV AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1
ENV AFL_TESTCACHE_SIZE=2

#
# Honggfuzz
#

# honggfuzz requires libfd and libunwid
RUN apt-get update -y && apt-get install -y libbfd-dev libunwind-dev
