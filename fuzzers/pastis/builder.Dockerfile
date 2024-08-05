ARG parent_image
FROM $parent_image

#
# AFLplusplus
#

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
RUN git clone https://github.com/AFLplusplus/AFLplusplus /afl

# Checkout a current commit
RUN cd /afl && git checkout 35f09e11a4373b0fb42c690d23127c144f72f73c

# Build without Python support as we don't need it.
# Set AFL_NO_X86 to skip flaky tests.
RUN cd /afl && \
    unset CFLAGS CXXFLAGS && \
    export CC=clang AFL_NO_X86=1 && \
    PYTHON_INCLUDE=/ make && \
    make install && \
    cp utils/aflpp_driver/libAFLDriver.a /

#
# Honggfuzz
#

# honggfuzz requires libfd and libunwid.
RUN apt-get update -y && \
    apt-get install -y \
    libbfd-dev \
    libunwind-dev \
    libblocksruntime-dev \
    liblzma-dev

# Copy honggfuzz PASTIS patch.
RUN mkdir /patches
COPY patches/honggfuzz-3a8f2ae-pastis.patch /patches

# Donwload honggfuzz oss-fuzz version (commit 3a8f2ae41604b6696e7bd5e5cdc0129ce49567c0)
RUN git clone https://github.com/google/honggfuzz.git /honggfuzz && \
    cd /honggfuzz && \
    git checkout 3a8f2ae41604b6696e7bd5e5cdc0129ce49567c0 && \
    cd ..

# Apply PASTIS patch.
RUN cd / && \
    patch -s -p0 < /patches/honggfuzz-3a8f2ae-pastis.patch

# Set CFLAGS use honggfuzz's defaults except for -mnative which can build CPU
# dependent code that may not work on the machines we actually fuzz on.
# Create an empty object file which will become the FUZZER_LIB lib (since
# honggfuzz doesn't need this when hfuzz-clang(++) is used).
RUN cd /honggfuzz && \
    CFLAGS="-O3 -funroll-loops" make && \
    touch empty_lib.c && \
    cc -c -o empty_lib.o empty_lib.c

# Use afl_driver.cpp for AFL, and StandaloneFuzzTargetMain.c for Eclipser.
RUN apt-get update && \
    apt-get install wget -y && \
    wget https://raw.githubusercontent.com/llvm/llvm-project/5feb80e748924606531ba28c97fe65145c65372e/compiler-rt/lib/fuzzer/standalone/StandaloneFuzzTargetMain.c -O /StandaloneFuzzTargetMain.c && \
    clang -O2 -c /StandaloneFuzzTargetMain.c && \
    ar rc /libStandaloneFuzzTarget.a StandaloneFuzzTargetMain.o && \
    rm /StandaloneFuzzTargetMain.c
