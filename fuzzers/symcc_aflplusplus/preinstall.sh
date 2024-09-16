#!/bin/bash

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

set -e

apt-get update && \
    apt-get install -y make build-essential git curl wget subversion \
        ninja-build python-is-python3 python3-pip zlib1g-dev inotify-tools sudo

apt-get update && \
    apt-get install -y lsb-release wget software-properties-common gnupg

(
  apt purge -y --auto-remove llvm clang
  pushd /tmp/
  wget https://apt.llvm.org/llvm.sh
  chmod +x llvm.sh
  ./llvm.sh 12
  popd
)

# qemu dependencies (for SymQEMU)
apt-get install -y git libglib2.0-dev libfdt-dev libpixman-1-dev zlib1g-dev ninja-build libncurses-dev libcurl4-openssl-dev bison flex

# we need a newer version of CMake
(
  apt purge -y --auto-remove cmake
  apt update && apt install -y software-properties-common lsb-release && apt clean all
  wget -O - https://apt.kitware.com/keys/kitware-archive-latest.asc 2>/dev/null | gpg --dearmor - | tee /etc/apt/trusted.gpg.d/kitware.gpg >/dev/null
  apt-add-repository "deb https://apt.kitware.com/ubuntu/ $(lsb_release -cs) main"
  apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 6AF7F09730B3F0A4
  apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 42D5A192B819C5DA
  apt update
  apt install kitware-archive-keyring
  rm /etc/apt/trusted.gpg.d/kitware.gpg
  apt update
  apt install -y cmake
)
cmake --version

pip install --upgrade pip
pip3 install --upgrade pip

pip install lit

update-alternatives \
  --install /usr/lib/llvm              llvm             /usr/lib/llvm-12  20 \
  --slave   /usr/bin/llvm-config       llvm-config      /usr/bin/llvm-config-12  \
    --slave   /usr/bin/llvm-ar           llvm-ar          /usr/bin/llvm-ar-12 \
    --slave   /usr/bin/llvm-as           llvm-as          /usr/bin/llvm-as-12 \
    --slave   /usr/bin/llvm-bcanalyzer   llvm-bcanalyzer  /usr/bin/llvm-bcanalyzer-12 \
    --slave   /usr/bin/llvm-c-test       llvm-c-test      /usr/bin/llvm-c-test-12 \
    --slave   /usr/bin/llvm-cov          llvm-cov         /usr/bin/llvm-cov-12 \
    --slave   /usr/bin/llvm-diff         llvm-diff        /usr/bin/llvm-diff-12 \
    --slave   /usr/bin/llvm-dis          llvm-dis         /usr/bin/llvm-dis-12 \
    --slave   /usr/bin/llvm-dwarfdump    llvm-dwarfdump   /usr/bin/llvm-dwarfdump-12 \
    --slave   /usr/bin/llvm-extract      llvm-extract     /usr/bin/llvm-extract-12 \
    --slave   /usr/bin/llvm-link         llvm-link        /usr/bin/llvm-link-12 \
    --slave   /usr/bin/llvm-mc           llvm-mc          /usr/bin/llvm-mc-12 \
    --slave   /usr/bin/llvm-nm           llvm-nm          /usr/bin/llvm-nm-12 \
    --slave   /usr/bin/llvm-objdump      llvm-objdump     /usr/bin/llvm-objdump-12 \
    --slave   /usr/bin/llvm-ranlib       llvm-ranlib      /usr/bin/llvm-ranlib-12 \
    --slave   /usr/bin/llvm-readobj      llvm-readobj     /usr/bin/llvm-readobj-12 \
    --slave   /usr/bin/llvm-rtdyld       llvm-rtdyld      /usr/bin/llvm-rtdyld-12 \
    --slave   /usr/bin/llvm-size         llvm-size        /usr/bin/llvm-size-12 \
    --slave   /usr/bin/llvm-stress       llvm-stress      /usr/bin/llvm-stress-12 \
    --slave   /usr/bin/llvm-symbolizer   llvm-symbolizer  /usr/bin/llvm-symbolizer-12 \
    --slave   /usr/bin/llvm-tblgen       llvm-tblgen      /usr/bin/llvm-tblgen-12

update-alternatives \
  --install /usr/bin/clang                 clang                  /usr/bin/clang-12     20 \
  --slave   /usr/bin/clang++               clang++                /usr/bin/clang++-12 \
  --slave   /usr/bin/clang-cpp             clang-cpp              /usr/bin/clang-cpp-12

# Uninstall old Rust
if which rustup; then rustup self uninstall -y; fi

# Install latest Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs > /tmp/rustup.sh && \
    sh /tmp/rustup.sh -y && \
    rm /tmp/rustup.sh

export PATH=$PATH:/root/.cargo/bin
echo PATH="$PATH:/root/.cargo/bin" >> ~/.bashrc
rustup default nightly-2022-09-18

(
  pushd /tmp/
  wget https://apt.llvm.org/llvm.sh
  chmod +x llvm.sh
  ./llvm.sh 12
  popd
)
