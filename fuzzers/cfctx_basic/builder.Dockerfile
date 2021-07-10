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

RUN apt-get update && \
    apt-get install -y wget libstdc++-5-dev libtool-bin automake flex bison \
                       libglib2.0-dev libpixman-1-dev python3-setuptools unzip \
                       apt-utils apt-transport-https ca-certificates \
                       binutils

RUN apt install -y lsb-release wget software-properties-common && wget https://apt.llvm.org/llvm.sh && chmod +x llvm.sh && ./llvm.sh 10

RUN update-alternatives \
      --install /usr/lib/llvm              llvm             /usr/lib/llvm-10  20 \
      --slave   /usr/bin/llvm-config       llvm-config      /usr/bin/llvm-config-10  \
        --slave   /usr/bin/llvm-ar           llvm-ar          /usr/bin/llvm-ar-10 \
        --slave   /usr/bin/llvm-as           llvm-as          /usr/bin/llvm-as-10 \
        --slave   /usr/bin/llvm-bcanalyzer   llvm-bcanalyzer  /usr/bin/llvm-bcanalyzer-10 \
        --slave   /usr/bin/llvm-c-test       llvm-c-test      /usr/bin/llvm-c-test-10 \
        --slave   /usr/bin/llvm-cov          llvm-cov         /usr/bin/llvm-cov-10 \
        --slave   /usr/bin/llvm-diff         llvm-diff        /usr/bin/llvm-diff-10 \
        --slave   /usr/bin/llvm-dis          llvm-dis         /usr/bin/llvm-dis-10 \
        --slave   /usr/bin/llvm-dwarfdump    llvm-dwarfdump   /usr/bin/llvm-dwarfdump-10 \
        --slave   /usr/bin/llvm-extract      llvm-extract     /usr/bin/llvm-extract-10 \
        --slave   /usr/bin/llvm-link         llvm-link        /usr/bin/llvm-link-10 \
        --slave   /usr/bin/llvm-mc           llvm-mc          /usr/bin/llvm-mc-10 \
        --slave   /usr/bin/llvm-nm           llvm-nm          /usr/bin/llvm-nm-10 \
        --slave   /usr/bin/llvm-objdump      llvm-objdump     /usr/bin/llvm-objdump-10 \
        --slave   /usr/bin/llvm-ranlib       llvm-ranlib      /usr/bin/llvm-ranlib-10 \
        --slave   /usr/bin/llvm-readobj      llvm-readobj     /usr/bin/llvm-readobj-10 \
        --slave   /usr/bin/llvm-rtdyld       llvm-rtdyld      /usr/bin/llvm-rtdyld-10 \
        --slave   /usr/bin/llvm-size         llvm-size        /usr/bin/llvm-size-10 \
        --slave   /usr/bin/llvm-stress       llvm-stress      /usr/bin/llvm-stress-10 \
        --slave   /usr/bin/llvm-symbolizer   llvm-symbolizer  /usr/bin/llvm-symbolizer-10 \
        --slave   /usr/bin/llvm-tblgen       llvm-tblgen      /usr/bin/llvm-tblgen-10 \
        --slave   /usr/bin/llc               llc              /usr/bin/llc-10 \
        --slave   /usr/bin/opt               opt              /usr/bin/opt-10 && \
    update-alternatives \
      --install /usr/bin/clang                 clang                  /usr/bin/clang-10     20 \
      --slave   /usr/bin/clang++               clang++                /usr/bin/clang++-10 \
      --slave   /usr/bin/clang-cpp             clang-cpp              /usr/bin/clang-cpp-10

ENV LLVM_DIR=/usr/lib/llvm-10
ENV LLVM_CONFIG=llvm-config-10

ENV GOPATH /go
ENV PATH="/go/bin:/dupfunc_ctx/bin/:${PATH}"
ENV LLVM_COMPILER_PATH=/usr/lib/llvm-10/bin

# Download and install the latest stable Go.
RUN cd /tmp && \
    wget https://storage.googleapis.com/golang/getgo/installer_linux && \
    chmod +x ./installer_linux && \
    SHELL="bash" ./installer_linux && \
    rm -rf ./installer_linux
ENV PATH $PATH:/root/.go/bin:$GOPATH/bin

RUN mkdir /go && go get github.com/SRI-CSL/gllvm/cmd/...@d01ecad84b901692e75ed05d51697b001fee40f0

# Download and compile SVF.
RUN git clone https://github.com/SVF-tools/SVF.git /SVF && \
   cd /SVF && git checkout SVF-2.1 && \
   git clone https://github.com/SVF-tools/Test-Suite.git && \
   cd Test-Suite && git checkout 72c679a49b943abb229fcb1844f68dff9cc7d522


# Download and compile sea-dsa dependencies
RUN apt-get install -y clang-format-10 build-essential g++ python-dev autotools-dev libicu-dev libbz2-dev
RUN apt-get remove -y libboost1.58-dev && add-apt-repository -y ppa:mhier/libboost-latest && apt update && apt install -y libboost1.67-dev
RUN add-apt-repository -y ppa:ubuntu-toolchain-r/test && apt update && apt install -y g++-7
# install cmake if too old (this is done for ffmpeg that uses an old builder)
ENV CMAKE_VERSION 3.19.2
RUN if dpkg --compare-versions $(cmake --version | head -n1| cut -d' ' -f 3) lt 3.10.2; then \
    apt-get update && apt-get install -y sudo && \
    wget https://github.com/Kitware/CMake/releases/download/v$CMAKE_VERSION/cmake-$CMAKE_VERSION-Linux-x86_64.sh && \
    chmod +x cmake-$CMAKE_VERSION-Linux-x86_64.sh && \
    ./cmake-$CMAKE_VERSION-Linux-x86_64.sh --skip-license --prefix="/usr/local" && \
    rm cmake-$CMAKE_VERSION-Linux-x86_64.sh && \
    SUDO_FORCE_REMOVE=yes apt-get remove --purge -y sudo && \
    rm -rf /usr/local/doc/cmake /usr/local/bin/cmake-gui; fi

# compile SVF
RUN cd /SVF && unset CFLAGS && unset CXXFLAGS && wget https://pastebin.com/raw/anzpb1FQ -O ../SVF-all.patch && GIT_COMMITTER_NAME='a' GIT_COMMITTER_EMAIL='a' git am -3 -k -u ../SVF-all.patch && ./build.sh debug 

# Download and compile sea-dsa
ENV PATH="${LLVM_DIR}/bin:${PATH}"
RUN git clone https://github.com/seahorn/sea-dsa.git -b dev10 /sea-dsa && \
    cd /sea-dsa && git checkout 594279ef14e5dc6b70322912988c98bfce7b7a10 && \
    mkdir build && cd build && \
    CFLAGS='' CXXFLAGS='' cmake -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_INSTALL_PREFIX=run -DLLVM_DIR=$LLVM_DIR/share/llvm/cmake .. && \
    cmake --build . --target install

ENV SEA_HOME=/sea-dsa

# Download and compile afl++.
RUN git clone https://github.com/AFLplusplus/AFLplusplus.git /afl && \
    cd /afl && \
    git checkout 74a6044b3fba496c1255f9aedbf5b7253ae29f0e && \
    sed -i 's|^#define CMPLOG_SOLVE|// #define CMPLOG_SOLVE|' include/config.h

# Build without Python support as we don't need it.
# Set AFL_NO_X86 to skip flaky tests.
RUN cd /afl && unset CFLAGS && unset CXXFLAGS && \
    export CC=clang && export AFL_NO_X86=1 && \
    PYTHON_INCLUDE=/ make LLVM_CONFIG=llvm-config-10 && make install

# RUN cd / && gclang -I /afl/include -c /afl/utils/aflpp_driver/aflpp_driver.c && \
#     ar ru libAFLDriver.a aflpp_driver.o

RUN wget https://raw.githubusercontent.com/llvm/llvm-project/5feb80e748924606531ba28c97fe65145c65372e/compiler-rt/lib/fuzzer/afl/afl_driver.cpp -O /afl_driver.cpp && \
    cd / && gclang++ -stdlib=libc++ -std=c++11 -O2 -c /afl_driver.cpp && \
    ar r /libAFLDriver.a afl_driver.o

ENV SVF_HOME=/SVF

# install python3 if too old (this is done for ffmpeg that uses an old builder)
ENV PYTHON_VERSION 3.8.6
RUN if dpkg --compare-versions $(python3 --version | head -n1| cut -d' ' -f 2) lt 3.8; then \
    apt-get update -y && apt-get install -y build-essential rsync curl zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev virtualenv libbz2-dev liblzma-dev libsqlite3-dev && \
    cd /tmp/ && \
    wget https://www.python.org/ftp/python/$PYTHON_VERSION/Python-$PYTHON_VERSION.tar.xz && \
    tar -xvf Python-$PYTHON_VERSION.tar.xz && \
    cd Python-$PYTHON_VERSION && \
    ./configure --enable-loadable-sqlite-extensions --enable-optimizations && \
    make -j install && \
    rm -r /tmp/Python-$PYTHON_VERSION.tar.xz /tmp/Python-$PYTHON_VERSION; fi

RUN cd / && python3 -m pip install brotli influxdb-client

# RUN git clone git@github.com:pietroborrello/AFLChen.git /dupfunc_ctx && \
#     cd /dupfunc_ctx && git checkout eaf3f05badcfb7f616fc986638142c0e3e03d7e5

RUN wget https://andreafioraldi.github.io/assets/dupfunc_ctx.tar.gz && \
    mkdir /dupfunc_ctx && tar xvf dupfunc_ctx.tar.gz -C /dupfunc_ctx && \
    rm dupfunc_ctx.tar.gz

RUN cd /dupfunc_ctx && unset CFLAGS && unset CXXFLAGS && \
    make -C passes SEA_HOME=/sea-dsa SVF_HOME=/SVF LLVM_CONFIG=llvm-config-10 && \
    cd bin && clang-10 -c ../aflpp-link-safe.c
