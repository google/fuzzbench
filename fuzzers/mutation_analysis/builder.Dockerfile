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
ARG map_mua

FROM gcr.io/fuzzbench/base-image AS base-image


FROM $parent_image

# Required packages
RUN DEBIAN_FRONTEND=noninteractive \
    apt-get update && \
    apt-get install -y \
        lsb-release \
        wget \
        software-properties-common gnupg \
        openjdk-11-jdk \
        zlib1g-dev \
        file \
        pipx \
        python3.8-venv

# llvm 15
RUN mkdir /llvm && \
    cd /llvm && \
    bash -c "$(wget -O - https://apt.llvm.org/llvm.sh)" && \
    wget https://apt.llvm.org/llvm.sh && \
    chmod +x llvm.sh && \
    ./llvm.sh 15

RUN update-alternatives --install \
            /usr/local/bin/llvm-config       llvm-config      /usr/lib/llvm-15/bin/llvm-config  200 \
    --slave /usr/local/bin/llvm-ar           llvm-ar          /usr/lib/llvm-15/bin/llvm-ar \
    --slave /usr/local/bin/llvm-as           llvm-as          /usr/lib/llvm-15/bin/llvm-as \
    --slave /usr/local/bin/llvm-bcanalyzer   llvm-bcanalyzer  /usr/lib/llvm-15/bin/llvm-bcanalyzer \
    --slave /usr/local/bin/llvm-cov          llvm-cov         /usr/lib/llvm-15/bin/llvm-cov \
    --slave /usr/local/bin/llvm-diff         llvm-diff        /usr/lib/llvm-15/bin/llvm-diff \
    --slave /usr/local/bin/llvm-dis          llvm-dis         /usr/lib/llvm-15/bin/llvm-dis \
    --slave /usr/local/bin/llvm-dwarfdump    llvm-dwarfdump   /usr/lib/llvm-15/bin/llvm-dwarfdump \
    --slave /usr/local/bin/llvm-extract      llvm-extract     /usr/lib/llvm-15/bin/llvm-extract \
    --slave /usr/local/bin/llvm-link         llvm-link        /usr/lib/llvm-15/bin/llvm-link \
    --slave /usr/local/bin/llvm-mc           llvm-mc          /usr/lib/llvm-15/bin/llvm-mc \
    --slave /usr/local/bin/llvm-mcmarkup     llvm-mcmarkup    /usr/lib/llvm-15/bin/llvm-mcmarkup \
    --slave /usr/local/bin/llvm-nm           llvm-nm          /usr/lib/llvm-15/bin/llvm-nm \
    --slave /usr/local/bin/llvm-objdump      llvm-objdump     /usr/lib/llvm-15/bin/llvm-objdump \
    --slave /usr/local/bin/llvm-ranlib       llvm-ranlib      /usr/lib/llvm-15/bin/llvm-ranlib \
    --slave /usr/local/bin/llvm-readobj      llvm-readobj     /usr/lib/llvm-15/bin/llvm-readobj \
    --slave /usr/local/bin/llvm-rtdyld       llvm-rtdyld      /usr/lib/llvm-15/bin/llvm-rtdyld \
    --slave /usr/local/bin/llvm-size         llvm-size        /usr/lib/llvm-15/bin/llvm-size \
    --slave /usr/local/bin/llvm-stress       llvm-stress      /usr/lib/llvm-15/bin/llvm-stress \
    --slave /usr/local/bin/llvm-symbolizer   llvm-symbolizer  /usr/lib/llvm-15/bin/llvm-symbolizer \
    --slave /usr/local/bin/llvm-tblgen       llvm-tblgen      /usr/lib/llvm-15/bin/llvm-tblgen \
    --slave /usr/local/bin/lld               lld              /usr/lib/llvm-15/bin/lld \
    --slave /usr/local/bin/clang             clang            /usr/lib/llvm-15/bin/clang \
    --slave /usr/local/bin/clang++           clang++          /usr/lib/llvm-15/bin/clang++

# wllvm
RUN pip3 install wllvm 

# gradle
RUN mkdir -p /tmp/gradle && \
    cd /tmp/gradle && \
    wget -q https://services.gradle.org/distributions/gradle-6.8-bin.zip && \
    unzip gradle-6.8-bin.zip && \
    mv gradle-6.8 /usr/local/gradle && \
    rm -r /tmp/gradle

ENV PATH "/usr/local/gradle/bin/:$PATH"

# gllvm
ENV PATH="${PATH}:/root/.cargo/bin:/usr/local/go/bin:/root/go/bin"
RUN mkdir /tmp/gllvm/ && \
    cd /tmp/gllvm/ && \
    wget -q -c https://dl.google.com/go/go1.16.15.linux-amd64.tar.gz -O - | tar -xz -C /usr/local && \
    go get github.com/SRI-CSL/gllvm/cmd/... && \
    rm -r /tmp/gllvm/

# hatch
RUN pipx install hatch

# mua_fuzzer_bench
RUN git clone https://github.com/phi-go/mua_fuzzer_bench /mutator && \
    cd /mutator && \
    git checkout 9689cd03b5a37224e0f7afdb664f92155df79bdf

RUN cd /mutator && \
    echo "llvmBinPath=/usr/lib/llvm-15/bin/" > gradle.properties

RUN ln -s /mutator/exec-recorder.py /exec-recorder.py && \
    ln -s /exec-recorder.py /bin/gclang-wrap && \
    ln -s /exec-recorder.py /bin/gclang++-wrap && \
    ln -s /mutator/mua_build_benchmark.py /bin/mua_build_benchmark

RUN mkdir /mua_build/ && chmod 777 /mua_build/
