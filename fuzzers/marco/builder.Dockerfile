ARG parent_image
FROM $parent_image

RUN apt-get update && apt-get install -y sudo
RUN apt-get -y install wget python3.8 python3-pip apt-transport-https \
    llvm-6.0 llvm-6.0-dev clang-6.0 llvm-6.0-tools libboost-all-dev texinfo \
    lsb-release software-properties-common autoconf curl zlib1g-dev \
	libgd-dev cmake vim redis-server libc++abi-dev libc++-dev
RUN apt-get -y install libtool-bin bison flex libpixman-1-dev git libglib2.0-dev nasm
RUN apt-get -y install strace
# RUN apt-get update && apt-get install clang clang++
# ENV CC=clang-6.0
# ENV CPP="clang-6.0 -E"
# ENV CXX=clang++-6.0
# ENV LD=ld.lld-6.0
# ENV LDSHARED="clang-6.0 -shared"
RUN CC=clang-6.0 CPP="clang++-6.0 -E" CXX=clang++-6.0 LD=ld.lld-6.0 LDSHARED="clang-6.0 -shared" pip install xlsxwriter pycrypto

# RUN add-apt-repository ppa:deadsnakes/ppa && apt update && apt install -y python3.8 python3.8-dev python3.8-pip python3.8-distutils
RUN python3 -m pip install pip
RUN python3 -m pip install pip --upgrade pip

RUN apt-get -y install libc-dev
RUN apt-get -y install build-essential
RUN apt-get -y install llvm-6.0-dev llvm-6.0-tools clang-6.0

RUN git clone https://github.com/Z3Prover/z3.git /z3 && \
		cd /z3 && git checkout z3-4.8.10 && \
		mkdir -p build && cd build && \
		cmake .. && make -j && make install


RUN apt-get -y install llvm-6.0-dev llvm-6.0-tools clang-6.0
RUN ln -s /usr/lib/llvm-6.0/include/llvm /usr/include/llvm
RUN ln -s /usr/lib/llvm-6.0/include/llvm-c /usr/include/llvm-c
RUN rm -rf /usr/local/bin/llvm-config && ln -s /usr/bin/llvm-config-6.0 /usr/local/bin/llvm-config

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | bash -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# ------------------------------ create directories required  ----------------------------------
USER root
RUN mkdir -p /workdir/input && \
    mkdir -p /outroot

# apt-get update
RUN apt-get install -y libpython3.8-dev
RUN apt-get install -y libprotobuf-dev protobuf-compiler
RUN pip3 install gensim numpy matplotlib annoy
RUN pip3 install transformers torch scikit-learn seaborn
RUN python3.8 -m pip install Cython
RUN python3.8 -m pip install nearpy
RUN python3.8 -m pip install sysv_ipc
RUN python3.8 -m pip install datasets
RUN python3.8 -m pip install tokenizers
RUN python3.8 -m pip install microdict
RUN python3.8 -m pip install z3-solver
RUN python3.8 -m pip install redis
RUN python3.8 -m pip install gputil
RUN python3.8 -m pip install psutil
RUN python3.8 -m pip install humanize
RUN python3.8 -m pip install networkit

RUN apt-get update && apt install -y libprotobuf-dev protobuf-compiler

RUN mkdir -p /data/

COPY src /data/src

RUN cd /data/src/CE && ./rebuild.sh

COPY scripts /data/scripts
RUN export CC=/data/src/CE/bin/ko-clang && \
	export CXX=/data/src/CE/bin/ko-clang++ && \
	export KO_CC=clang-6.0 && \
	export KO_CXX=clang++-6.0 && \
	export KO_DONT_OPTIMIZE=1 && \
	$CC -c /data/scripts/StandaloneFuzzTargetMain.c -fPIC -o /driver.o && \
	ar r /driver.a /driver.o


WORKDIR /workdir



# INSTALL AFL++


RUN apt-get update && \
    apt-get install -y \
        build-essential \
        python3-dev \
        python3-setuptools \
        automake \
        cmake \
        git \
        flex \
        bison \
        libglib2.0-dev \
        libpixman-1-dev \
        cargo \
        libgtk-3-dev \
        # for QEMU mode
        ninja-build \
        gcc-$(gcc --version|head -n1|sed 's/\..*//'|sed 's/.* //')-plugin-dev \
        libstdc++-$(gcc --version|head -n1|sed 's/\..*//'|sed 's/.* //')-dev

# Download afl++.
RUN git clone -b dev https://github.com/AFLplusplus/AFLplusplus /afl-base && \
    cd /afl-base && \
    git checkout 97644836935020b9f42688bb6530f08f536644a9 || \
    true

# Build without Python support as we don't need it.
# Set AFL_NO_X86 to skip flaky tests.
RUN cd /afl-base && \
    unset CFLAGS CXXFLAGS && \
    export CC=clang AFL_NO_X86=1 && \
    PYTHON_INCLUDE=/ make && \
    make install && \
    cp utils/aflpp_driver/libAFLDriver.a /libAFLDriver-base.a