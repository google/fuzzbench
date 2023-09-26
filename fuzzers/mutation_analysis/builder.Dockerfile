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


# WORKDIR /home/
# RUN mkdir -p downloads
# WORKDIR /home/downloads
# RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
# RUN python3 get-pip.py

RUN pip3 install wllvm

# ENV PATH "/root/toolchains/build/llvm+clang-901-x86_64-linux-gnu_build/bin/:$PATH"
ENV LLVM_COMPILER "clang"

RUN mkdir -p /tmp/gradle && \
    cd /tmp/gradle && \
    wget -q https://services.gradle.org/distributions/gradle-6.8-bin.zip && \
    unzip gradle-6.8-bin.zip && \
    mv gradle-6.8 /usr/local/gradle && \
    rm -r /tmp/gradle

ENV PATH "/usr/local/gradle/bin/:$PATH"

#### install gllvm
# WORKDIR /root/

# RUN wget -q -c https://dl.google.com/go/go1.16.15.linux-amd64.tar.gz -O - | tar -xz -C /usr/local

# ENV PATH="${PATH}:/root/.cargo/bin:/usr/local/go/bin:/root/go/bin"

# RUN go get github.com/SRI-CSL/gllvm/cmd/...

ENV PATH="${PATH}:/root/.cargo/bin:/usr/local/go/bin:/root/go/bin"

RUN mkdir /tmp/gllvm/ && \
    cd /tmp/gllvm/ && \
    wget -q -c https://dl.google.com/go/go1.16.15.linux-amd64.tar.gz -O - | tar -xz -C /usr/local && \
    go get github.com/SRI-CSL/gllvm/cmd/... && \
    rm -r /tmp/gllvm/

# TODO remove
# copy main.cc to /home/mutator/programs/common/main.cc while framework is not done
COPY main.cc /home/mutator/dockerfiles/programs/common/main.cc

# mutator


# WORKDIR /home/

# # RUN mkdir mutator
# WORKDIR /home/mutator

# ARG DEBIAN_FRONTEND=noninteractive
# RUN DEBIAN_FRONTEND=noninteractive apt-get update && apt-get install -y openjdk-11-jdk zlib1g-dev
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
# COPY mua_fuzzer_bench /mutator

# COPY modules /home/mutator/modules
# COPY build.gradle /home/mutator/
# COPY run_mutation.py /home/mutator/
# RUN chmod +x run_mutation.py
# COPY settings.gradle /home/mutator
# RUN cd /mutator && \
#     echo "llvmBinPath=/usr/local/bin/" > gradle.properties && \
#     gradle clean && \
#     gradle build


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