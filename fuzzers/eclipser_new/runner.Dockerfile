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

# Install dotnet, qemu and other Eclipser deps.
RUN sed -i -- 's/# deb-src/deb-src/g' /etc/apt/sources.list
RUN apt-get update -y && \
    apt-get build-dep -y qemu && \
    apt-get install -y \
        apt-transport-https \
        libtool \
        libtool-bin \
        wget \
        automake \
        autoconf \
        bison \
        git \
        gdb \
        python2

# Use a copy of
# https://packages.microsoft.com/config/ubuntu/16.04/packages-microsoft-prod.deb
# to avoid network flakiness.
RUN wget -q https://storage.googleapis.com/fuzzbench-files/packages-microsoft-prod.deb -O packages-microsoft-prod.deb && \
    dpkg -i packages-microsoft-prod.deb && \
    apt-get update -y && \
    apt-get install -y dotnet-sdk-2.1 dotnet-runtime-2.1 && \
    rm packages-microsoft-prod.deb

# Build Eclipser.
RUN git clone https://github.com/SoftSec-KAIST/Eclipser.git /Eclipser && \
    cd /Eclipser && \
    git checkout ba1d7a55c168f7c19ecceb788a81ea07c2625e45 && \
    ln -sf /usr/bin/python2.7 /usr/local/bin/python && \
    make -j && \
    ln -sf /usr/local/bin/python3.10 /usr/local/bin/python
