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

RUN git clone -b master https://github.com/gtt1995/GMFuzzer.git /gmfuzzer
RUN git clone -b fuzzers https://github.com/gtt1995/GMFuzzer.git /fuzzers
#
# Honggfuzz
#

# honggfuzz requires libfd and libunwid.
RUN apt-get install -y \
    libbfd-dev \
    libunwind-dev \
    libblocksruntime-dev \
    liblzma-dev

#COPY honggfuzz /honggfuzz

# Set CFLAGS use honggfuzz's defaults except for -mnative which can build CPU
# dependent code that may not work on the machines we actually fuzz on.
# Create an empty object file which will become the FUZZER_LIB lib (since
# honggfuzz doesn't need this when hfuzz-clang(++) is used).
RUN cp -r /fuzzers/honggfuzz /honggfuzz && \
    cd /honggfuzz && \
    CFLAGS="-O3 -funroll-loops" make && \
    touch empty_lib.c && \
    cc -c -o empty_lib.o empty_lib.c


RUN cd /gmfuzzer &&\
    (for f in *.cpp; do \
      clang++ -stdlib=libc++ -fPIC -O2 -std=c++11 $f -c & \
    done && wait) && \
    ar r /usr/lib/libHCFUZZER.a *.o
