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


FROM gcr.io/fuzzbench/base-image AS base-image


FROM $parent_image

RUN apt-get update && apt-get install -y \
    lsb-release wget software-properties-common gnupg
RUN mkdir /llvm && \
    cd /llvm && \
    bash -c "$(wget -O - https://apt.llvm.org/llvm.sh)" && \
    wget https://apt.llvm.org/llvm.sh && \
    chmod +x llvm.sh && \
    ./llvm.sh 15

# WORKDIR /home/
# RUN mkdir -p downloads
# WORKDIR /home/downloads
# RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
# RUN python3 get-pip.py

RUN pip3 install wllvm 

# ENV PATH "/root/toolchains/build/llvm+clang-901-x86_64-linux-gnu_build/bin/:$PATH"
# ENV LLVM_COMPILER "clang"

RUN mkdir -p /tmp/gradle && \
    cd /tmp/gradle && \
    wget -q https://services.gradle.org/distributions/gradle-6.8-bin.zip && \
    unzip gradle-6.8-bin.zip && \
    mv gradle-6.8 /usr/local/gradle && \
    rm -r /tmp/gradle

ENV PATH "/usr/local/gradle/bin/:$PATH"

#### install gllvm
ENV PATH="${PATH}:/root/.cargo/bin:/usr/local/go/bin:/root/go/bin"
RUN mkdir /tmp/gllvm/ && \
    cd /tmp/gllvm/ && \
    wget -q -c https://dl.google.com/go/go1.16.15.linux-amd64.tar.gz -O - | tar -xz -C /usr/local && \
    go get github.com/SRI-CSL/gllvm/cmd/... && \
    rm -r /tmp/gllvm/

RUN DEBIAN_FRONTEND=noninteractive apt-get update && apt-get install -y openjdk-11-jdk zlib1g-dev file
        # cmake \
        # binutils-dev \
        # libcurl4-openssl-dev \
        # zlib1g-dev \
        # libdw-dev \
        # libiberty-dev \
        # libssl-dev \
        # libelf-dev \
        # libdw-dev \
        # libidn2-dev \
        # libidn2-0 \
        # idn2 \
        # libstdc++6

# RUN git clone https://github.com/CISPA-SysSec/mua_fuzzer_bench mutator
COPY mua_fuzzer_bench /mutator

# COPY modules /home/mutator/modules
# COPY build.gradle /home/mutator/
# COPY run_mutation.py /home/mutator/
# RUN chmod +x run_mutation.py
# COPY settings.gradle /home/mutator
RUN cd /mutator && \
    echo "llvmBinPath=/usr/lib/llvm-15/bin/" > gradle.properties
# RUN cd /mutator && gradle clean && gradle build
# RUN ldconfig /mutator/build/install/LLVM_Mutation_Tool/lib/

# RUN ln /usr/bin/llvm-link-15 /bin/llvm-link 
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

RUN apt-get update && apt-get install -y pipx python3.8-venv
RUN pipx install hatch

RUN ln -s /mutator/exec-recorder.py /exec-recorder.py 
RUN ln -s /exec-recorder.py /bin/gclang-wrap
RUN ln -s /exec-recorder.py /bin/gclang++-wrap
RUN ln -s /mutator/mua_build_benchmark.py /bin/mua_build_benchmark


# # set library paths for used shared libraries s.t. the system finds them
# ENV LD_LIBRARY_PATH /home/mutator/build/install/LLVM_Mutation_Tool/lib/
# # For all subjects provide the path to the default main here. This is based on oss-fuzz convention.
# ENV LIB_FUZZING_ENGINE="/home/mutator/programs/common/main.cc"
# ENV CC=gclang
# ENV CXX=gclang++ 

########

# ENV LF_PATH /tmp/libfuzzer.zip

# # Use a libFuzzer version that supports clang source-based coverage.
# # This libfuzzer is 0b5e6b11c358e704384520dc036eddb5da1c68bf with
# # https://github.com/google/fuzzbench/blob/cf86138081ec705a47ce0a4bab07b5737292e7e0/fuzzers/coverage/patch.diff
# # applied.

# RUN wget https://storage.googleapis.com/fuzzbench-artifacts/libfuzzer-coverage.zip -O $LF_PATH && \
#     echo "cc78179f6096cae4b799d0cc9436f000cc0be9b1fb59500d16b14b1585d46b61 $LF_PATH" | sha256sum --check --status && \
#     mkdir /tmp/libfuzzer && \
#     cd /tmp/libfuzzer && \
#     unzip $LF_PATH  && \
#     bash build.sh && \
#     cp libFuzzer.a /usr/lib && \
#     rm -rf /tmp/libfuzzer $LF_PATH


# clear && fuzzer_build && mua_build_benchmark && pushd /mutator && gradle build && ldconfig /mutator/build/install/LLVM_Mutation_Tool/lib/ && pipx run hatch run src/mua_fuzzer_benchmark/eval.py locator_local --config-path /tmp/config.json --result-path /tmp/test/ ; popd