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
#COPY AFLplusplus /aflplusplus

# Build without Python support as we don't need it.
# Set AFL_NO_X86 to skip flaky tests.
RUN cp -r /fuzzers/AFLplusplus /aflplusplus && \
    cd /aflplusplus && \
    unset CFLAGS CXXFLAGS && \
    export CC=clang AFL_NO_X86=1 && \
    PYTHON_INCLUDE=/ make && \
    make install && \
    cp utils/aflpp_driver/libAFLDriver.a /  && \
    make -C custom_mutators/autotokens && \
    cp -f custom_mutators/autotokens/autotokens.so .


RUN cd /gmfuzzer &&\
    (for f in *.cpp; do \
      clang++ -stdlib=libc++ -fPIC -O2 -std=c++11 $f -c & \
    done && wait) && \
    ar r /usr/lib/libHCFUZZER.a *.o
