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

# FROM ubuntu:focal
# ARG DEBIAN_FRONTEND=noninteractive

ARG parent_image
FROM $parent_image

RUN apt-get update && \
    apt-get -y install --no-install-suggests --no-install-recommends \
    automake \
    cmake \
    meson \
    ninja-build \
    bison flex \
    build-essential \
    git \
    binutils \
    python3 python3-dev python3-setuptools python-is-python3 \
    libtool libtool-bin \
    libglib2.0-dev \
    wget vim jupp nano bash-completion less \
    apt-utils apt-transport-https ca-certificates gnupg dialog \
    libpixman-1-dev \
    gnuplot-nox \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Add ~/.local/bin and /usr/local/go/bin to the PATH
RUN mkdir -p /home/$USER_NAME/.local/bin
ENV PATH="/home/.local/bin:/usr/local/go/bin:/fox/gllvm_bins:${PATH}"
RUN echo "export PATH=$PATH" >> ~/.bashrc

RUN apt-get update && \
    apt-get -y install --no-install-suggests --no-install-recommends \
    lsb-release wget software-properties-common gnupg

RUN wget https://apt.llvm.org/llvm.sh
RUN chmod +x llvm.sh
RUN sudo ./llvm.sh 15

RUN update-alternatives --install /usr/bin/clang clang /usr/bin/clang-15 10 \
                        --slave /usr/bin/clang++ clang++ /usr/bin/clang++-15 \
                        --slave /usr/bin/opt opt /usr/bin/opt-15
RUN update-alternatives --install /usr/lib/llvm llvm /usr/lib/llvm-15 20 \
                        --slave /usr/bin/llvm-config llvm-config /usr/bin/llvm-config-15 \
                        --slave /usr/bin/llvm-link llvm-link /usr/bin/llvm-link-15

ENV LLVM_CONFIG=llvm-config-15

# Import and setup FOX : TODO : add publie repo
RUN git clone https://github.com/FOX-Fuzz/FOX /fox
RUN rm -f /dev/shm/*

RUN cd /fox && \
    unset CFLAGS CXXFLAGS && \
    export CC=clang-15 AFL_NO_X86=1 && \
    PYTHON_INCLUDE=/ make && \
    cp utils/aflpp_driver/libAFLDriver.a /

RUN rm /usr/local/bin/llvm-nm
RUN sudo ln -s /usr/bin/llvm-nm-15 /usr/local/bin/llvm-nm

RUN rm -rf /usr/local/bin/clang*
