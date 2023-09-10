FROM fuzzer_base/afl as afl
FROM fuzzer_base/aflfast as aflfast
FROM fuzzer_base/angora as angora
FROM fuzzer_base/fairfuzz as fairfuzz
FROM fuzzer_base/lafintel as lafintel
FROM fuzzer_base/learnafl as learnafl
FROM fuzzer_base/libfuzzer as libfuzzer
FROM fuzzer_base/mopt as mopt
FROM fuzzer_base/radamsa as radamsa
FROM fuzzer_base/redqueen as redqueen

FROM autofz_bench/afl as bench_afl
FROM autofz_bench/angora as bench_angora
FROM autofz_bench/lafintel as bench_lafintel
FROM autofz_bench/libfuzzer as bench_libfuzzer
FROM autofz_bench/radamsa as bench_radamsa
FROM autofz_bench/redqueen as bench_redqueen
FROM autofz_bench/coverage as bench_coverage

FROM ubuntu:16.04

ARG USER
ARG UID
ARG GID

SHELL ["/bin/bash", "-c"]

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONIOENCODING=utf8 \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

# install proper tools
RUN apt-get update && \
    apt-get install -y vim tmux nano htop autoconf automake build-essential libtool cmake git sudo software-properties-common gperf libselinux1-dev  bison texinfo flex zlib1g-dev libexpat1-dev libmpg123-dev wget curl python3-pip python-pip unzip pkg-config clang llvm-dev apt-transport-https ca-certificates libc++-dev gcc-5-plugin-dev zip tree re2c bison libtool

# QSYM Part ! it alters /usr/local, so we build it here
RUN curl -fsSL -o- https://bootstrap.pypa.io/pip/2.7/get-pip.py | python2

RUN git clone --depth 1  https://github.com/fuyu0425/qsym /fuzzer/qsym

WORKDIR /fuzzer/qsym
RUN sed -i '23,25 s/^/#/' setup.py && sed -i '4,7 s/^/#/' setup.sh && \
    ./setup.sh && pip2 install .


RUN apt-get install -y git build-essential wget zlib1g-dev golang-go python-pip python-dev build-essential cmake

# lava
RUN apt install -y libglib2.0-dev gtk-doc-tools libtiff-dev libpng-dev \
  nasm tcl-dev libacl1-dev libgmp-dev libcap-dev

# fuzzer-test-suite
RUN apt install -y golang libarchive-dev libpng-dev ragel gtk-doc-tools libfreetype6-dev libglib2.0-dev libcairo2-dev \
  binutils-dev libgcrypt20-dev libdbus-glib-1-dev libgirepository1.0-dev libgss-dev bzip2 libbz2-dev libc-ares-dev libfreetype6-dev libglib2.0-dev \
  libssh-dev libssl-dev libxml2-dev libturbojpeg nasm liblzma-dev subversion

RUN apt-get install -y zip autoconf automake libtool bison re2c pkg-config flex bison dbus-cpp-dev

RUN sudo apt install -y libunwind-dev

RUN apt update && apt install -y protobuf-compiler cgroup-tools lcov

# New benchmark
## file
RUN apt install -y make autoconf automake libtool shtool

# Fuzzbench
RUN apt install -y ninja-build wget cmake

RUN echo "deb http://apt.llvm.org/xenial/ llvm-toolchain-xenial-12 main" >> /etc/apt/sources.list && \
  echo "deb-src http://apt.llvm.org/xenial/ llvm-toolchain-xenial-12 main" >> /etc/apt/sources.list && \
  apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 15CF4D18AF4F7421 && \
  apt update && \
    apt-get install -y clang-12 llvm-12-dev lld-12 lld-12 clangd-12 lldb-12 libc++1-12 libc++-12-dev libc++abi-12-dev && \
  update-alternatives --install /usr/bin/clang clang /usr/bin/clang-12 100 && \
  update-alternatives --install /usr/bin/clang++ clang++ /usr/bin/clang++-12 100 && \
  update-alternatives --install /usr/bin/llvm-config llvm-config /usr/bin/llvm-config-12 100 && \
  update-alternatives --install /usr/bin/lldb lldb /usr/bin/lldb-12 100 && \
  update-alternatives --install /usr/bin/llvm-cov llvm-cov /usr/bin/llvm-cov-12 100


# # RUN mkdir /llvm && \
# #   cd /llvm && \
# #   wget http://releases.llvm.org/9.0.0/llvm-9.0.0.src.tar.xz -O llvm.tar.xz && tar xf llvm.tar.xz && \
# #   wget http://releases.llvm.org/9.0.0/compiler-rt-9.0.0.src.tar.xz -O compiler-rt.tar.xz && tar xf compiler-rt.tar.xz

RUN mkdir /llvm && \
    cd /llvm && \
    wget https://github.com/llvm/llvm-project/releases/download/llvmorg-12.0.0/llvm-12.0.0.src.tar.xz -O llvm.tar.xz && tar xf llvm.tar.xz && \
    wget https://github.com/llvm/llvm-project/releases/download/llvmorg-12.0.0/compiler-rt-12.0.0.src.tar.xz -O compiler-rt.tar.xz && tar xf compiler-rt.tar.xz

COPY --chown=$UID:$GID --from=afl /fuzzer /fuzzer
COPY --chown=$UID:$GID --from=aflfast /fuzzer /fuzzer
COPY --chown=$UID:$GID --from=angora /fuzzer /fuzzer
COPY --chown=$UID:$GID --from=fairfuzz /fuzzer /fuzzer
COPY --chown=$UID:$GID --from=lafintel /fuzzer /fuzzer
COPY --chown=$UID:$GID --from=learnafl /fuzzer /fuzzer
COPY --chown=$UID:$GID --from=libfuzzer /fuzzer /fuzzer
COPY --chown=$UID:$GID --from=mopt /fuzzer /fuzzer
COPY --chown=$UID:$GID --from=radamsa /fuzzer /fuzzer
COPY --chown=$UID:$GID --from=redqueen /fuzzer /fuzzer

COPY --chown=$UID:$GID --from=bench_afl /d /d
COPY --chown=$UID:$GID --from=bench_angora /d /d
COPY --chown=$UID:$GID --from=bench_lafintel /d /d
COPY --chown=$UID:$GID --from=bench_radamsa /d /d
COPY --chown=$UID:$GID --from=bench_redqueen /d /d

COPY --chown=$UID:$GID --from=bench_afl /seeds /seeds

COPY --chown=$UID:$GID --from=bench_libfuzzer /d /d

COPY --chown=$UID:$GID --from=bench_coverage /d /d

# Used to calculate coverage. We need source code
COPY --chown=$UID:$GID --from=bench_coverage /autofz_bench /autofz_bench

USER root
RUN cp /fuzzer/LearnAFL/learning_engine.py /usr/local/bin

# Reset to normal compilers
ENV CC="gcc" CXX="g++"

# start install autofz dependencies

# install newer python3
RUN apt install -y --no-install-recommends make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl libncurses5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev tk-dev ca-certificates

WORKDIR /root

RUN wget https://www.python.org/ftp/python/3.9.4/Python-3.9.4.tgz \
    && tar xf Python-3.9.4.tgz \
    && cd Python-3.9.4 \
    && ./configure \
    && make -j8 install

RUN curl https://bootstrap.pypa.io/get-pip.py -o /get-pip.py && python3 /get-pip.py

# set timezone
ENV TZ=America/New_York
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# some useful tools
RUN apt-get install -y zsh locales direnv highlight jq
RUN locale-gen en_US.UTF-8

COPY init.sh /
COPY afl-cov/ /afl-cov

COPY autofz/ /autofz/autofz
COPY draw/   /autofz/draw
COPY setup.py  /autofz/
COPY requirements.txt  /autofz/

RUN pip install /autofz

ENV PATH="/autofz/autofz:/afl-cov:${PATH}"

# Add autofz user with proper UID and GID (2000 when this image is built)

RUN groupadd -g $GID -o $USER
RUN adduser --disabled-password --gecos '' -u $UID -gid $GID ${USER}
RUN adduser ${USER} sudo
RUN echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

USER $USER

WORKDIR /home/$USER
