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
FROM $parent_image

RUN apt-get update && apt-get install -y sudo make build-essential git wget tree vim gdb zstd libzstd-dev libjbig-dev libselinux-dev bash

SHELL ["/bin/bash", "-c"]

RUN wget -O - https://apt.llvm.org/llvm-snapshot.gpg.key | apt-key add -

RUN echo "deb http://apt.llvm.org/focal/ llvm-toolchain-focal main" >> /etc/apt/sources.list
RUN echo "deb-src http://apt.llvm.org/focal/ llvm-toolchain-focal main" >> /etc/apt/sources.list
RUN echo "# 17" >> /etc/apt/sources.list
RUN echo "deb http://apt.llvm.org/focal/ llvm-toolchain-focal-17 main" >> /etc/apt/sources.list
RUN echo "deb-src http://apt.llvm.org/focal/ llvm-toolchain-focal-17 main" >> /etc/apt/sources.list

RUN apt-get update && apt-get install -y clang-17 lld-17 llvm-17-dev \
	libc++-17-dev libc++abi-17-dev gcc-10 gcc-10-plugin-dev libstdc++-10-dev \
	libssl-dev cargo autopoint

RUN update-alternatives \
	--install /usr/lib/llvm              llvm             /usr/lib/llvm-17  1000 \
	--slave   /usr/bin/llvm-config       llvm-config      /usr/bin/llvm-config-17  \
	--slave   /usr/bin/llvm-ar           llvm-ar          /usr/bin/llvm-ar-17 \
	--slave   /usr/bin/llvm-as           llvm-as          /usr/bin/llvm-as-17 \
	--slave   /usr/bin/llvm-bcanalyzer   llvm-bcanalyzer  /usr/bin/llvm-bcanalyzer-17 \
	--slave   /usr/bin/llvm-c-test       llvm-c-test      /usr/bin/llvm-c-test-17 \
	--slave   /usr/bin/llvm-cov          llvm-cov         /usr/bin/llvm-cov-17 \
	--slave   /usr/bin/llvm-diff         llvm-diff        /usr/bin/llvm-diff-17 \
	--slave   /usr/bin/llvm-dis          llvm-dis         /usr/bin/llvm-dis-17 \
	--slave   /usr/bin/llvm-dwarfdump    llvm-dwarfdump   /usr/bin/llvm-dwarfdump-17 \
	--slave   /usr/bin/llvm-extract      llvm-extract     /usr/bin/llvm-extract-17 \
	--slave   /usr/bin/llvm-link         llvm-link        /usr/bin/llvm-link-17 \
	--slave   /usr/bin/llvm-mc           llvm-mc          /usr/bin/llvm-mc-17 \
	--slave   /usr/bin/llvm-nm           llvm-nm          /usr/bin/llvm-nm-17 \
	--slave   /usr/bin/llvm-objdump      llvm-objdump     /usr/bin/llvm-objdump-17 \
	--slave   /usr/bin/llvm-ranlib       llvm-ranlib      /usr/bin/llvm-ranlib-17 \
	--slave   /usr/bin/llvm-readobj      llvm-readobj     /usr/bin/llvm-readobj-17 \
	--slave   /usr/bin/llvm-rtdyld       llvm-rtdyld      /usr/bin/llvm-rtdyld-17 \
	--slave   /usr/bin/llvm-size         llvm-size        /usr/bin/llvm-size-17 \
	--slave   /usr/bin/llvm-stress       llvm-stress      /usr/bin/llvm-stress-17 \
	--slave   /usr/bin/llvm-symbolizer   llvm-symbolizer  /usr/bin/llvm-symbolizer-17 \
	--slave   /usr/bin/llvm-tblgen       llvm-tblgen      /usr/bin/llvm-tblgen-17

RUN update-alternatives \
	--install /usr/bin/clang                 clang                  /usr/bin/clang-17     1000 \
	--slave   /usr/bin/clang++               clang++                /usr/bin/clang++-17 \
	--slave   /usr/bin/clang-cpp             clang-cpp              /usr/bin/clang-cpp-17 \
	--slave   /usr/bin/ld.lld                   lld                    /usr/bin/ld.lld-17

# Uninstall old Rust
RUN if which rustup; then rustup self uninstall -y; fi

# Install latest Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs > /rustup.sh && \
    sh /rustup.sh -y

ENV PATH="/root/.cargo/bin:${PATH}"

RUN rm -rf /usr/local/bin/clang /usr/local/bin/clang++ /usr/local/bin/llvm*
RUN rm -rf /usr/local/lib/clang
RUN rm -rf /usr/local/include/clang
RUN rm -rf /usr/local/share/clang

# RUN rm /usr/local/bin/clang /usr/local/bin/clang++ /usr/local/bin/clang-cpp
# ENV PATH="/usr/bin:/usr/local/bin:$PATH"

# RUN ls /usr/lib/llvm-17/include/llvm && exit 1

# RUN clang --version | grep "clang version 17" || { echo "Clang version is not 17"; exit 1; }

RUN git clone -b fx-no-tail-opt1 https://github.com/fEst1ck/path-cov.git /path-cov

RUN cd /path-cov && \
	git checkout bb900e89e14766ebd9d4af27cae0862bdb37de9b && \
	cargo build --release

RUN git clone -b edge-priority https://github.com/path-cov-fuzzer/newpathAFLplusplus.git /path-afl

# RUN clang++-17 -v -E -x c++ - < /dev/null && eixt 1

RUN cd /path-afl && \
	which clang-17 && \
	which clang && \
	clang --version && \
	clang++ -stdlib=libc++ -c hashcompare.cpp && \
	ar rcs libhashcompare.a hashcompare.o && \
	cp /path-cov/target/release/libpath_reduction.so .

# RUN which llvm-config-17 || { echo "llvm-config-17 not found"; exit 1; }

RUN cd /path-afl && \
	export CC=clang && \
	export CXX=clang++ && \
	export AFL_NO_X86=1 && \
	unset CFLAGS CXXFLAGS && \
	PYTHON_INCLUDE=/ && \
	LLVM_CONFIG=llvm-config-17 LD_LIBRARY_PATH="/path-afl" CFLAGS="-I/path-afl/fuzzing_support" LDFLAGS="-L/path-afl -lcrypto -lhashcompare -lc++ -lpath_reduction" make
# RUN	export CC=clang && \
# 	export CXX=clang++ && \
# 	export AFL_NO_X86=1 && \
# 	export PYTHON_INCLUDE=/ && \
# 	LLVM_CONFIG=llvm-config-17 LD_LIBRARY_PATH="/path-afl" CFLAGS="-I/path-afl/fuzzing_support" LDFLAGS="-L/path-afl -lcrypto -lhashcompare -lstdc++ -lpath_reduction" make -e -C utils/aflpp_driver || exit 1

RUN apt install g++

# Build without Python support as we don't need it.
# Set AFL_NO_X86 to skip flaky tests.
RUN cd /path-afl && cp utils/aflpp_driver/libAFLDriver.a /

RUN cp /usr/lib/x86_64-linux-gnu/libpython3.8.so.1.0 /

RUN cp /usr/lib/llvm-17/lib/libc++.so.1 /
RUN cp /usr/lib/llvm-17/lib/libc++abi.so.1 /

