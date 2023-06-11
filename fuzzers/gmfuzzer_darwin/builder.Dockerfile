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
#Build custom_mutators for aflplusplusplus

#
# AFL
#

#COPY AFL /afl
RUN cp -r /fuzzers/AFL /afl && \
    cd /afl && \
    CFLAGS= CXXFLAGS= AFL_NO_X86=1 make 


# Use afl_driver.cpp from LLVM as our fuzzing library.
RUN apt-get install wget -y && \
    wget https://raw.githubusercontent.com/llvm/llvm-project/5feb80e748924606531ba28c97fe65145c65372e/compiler-rt/lib/fuzzer/afl/afl_driver.cpp -O /afl/afl_driver.cpp && \
    clang -Wno-pointer-sign -c /afl/llvm_mode/afl-llvm-rt.o.c -I/afl && \
    clang++ -stdlib=libc++ -std=c++11 -O2 -c /afl/afl_driver.cpp && \
    ar r /libAFL.a *.o


#
#darwin
#

#COPY DARWIN /darwin

RUN cp -r /fuzzers/DARWIN /darwin && \
    cd /darwin && \
    CFLAGS= CXXFLAGS= AFL_NO_X86=1 make

# Use afl_driver.cpp from LLVM as our fuzzing library.
RUN wget https://raw.githubusercontent.com/llvm/llvm-project/5feb80e748924606531ba28c97fe65145c65372e/compiler-rt/lib/fuzzer/afl/afl_driver.cpp -O /darwin/afl_driver.cpp && \
    clang -Wno-pointer-sign -c /darwin/llvm_mode/afl-llvm-rt.o.c -I/darwin && \
    clang++ -stdlib=libc++ -std=c++11 -O2 -c /darwin/afl_driver.cpp && \
    ar r /libDARWIN.a *.o

#
#ecofuzz
#

#COPY EcoFuzz /EcoFuzz

RUN cp -r /fuzzers/EcoFuzz/EcoFuzz /ecofuzz && \
    cd /ecofuzz && \
    AFL_NO_X86=1 make

# Use afl_driver.cpp from LLVM as our fuzzing library.
RUN wget https://raw.githubusercontent.com/llvm/llvm-project/5feb80e748924606531ba28c97fe65145c65372e/compiler-rt/lib/fuzzer/afl/afl_driver.cpp -O /ecofuzz/afl_driver.cpp && \
    clang -Wno-pointer-sign -c /ecofuzz/llvm_mode/afl-llvm-rt.o.c -I/ecofuzz && \
    clang++ -stdlib=libc++ -std=c++11 -O2 -c /ecofuzz/afl_driver.cpp && \
    ar r /libECOFUZZ.a *.o


#
#entropic
#

RUN git clone https://github.com/llvm/llvm-project.git /llvm-project && \
    cd /llvm-project && \
    git checkout 5cda4dc7b4d28fcd11307d4234c513ff779a1c6f && \
    cd compiler-rt/lib/fuzzer && \
    (for f in *.cpp; do \
      clang++ -stdlib=libc++ -fPIC -O2 -std=c++11 $f -c & \
    done && wait) && \
    ar r /libENTROPIC.a *.o

#
#fafuzz
#

#COPY fafuzz /fafuzz
RUN cp -r /fuzzers/fafuzz /fafuzz && \
    cd /fafuzz && \
    AFL_NO_X86=1 make

# Use afl_driver.cpp from LLVM as our fuzzing library.
RUN apt-get install wget -y && \
    wget https://raw.githubusercontent.com/llvm/llvm-project/5feb80e748924606531ba28c97fe65145c65372e/compiler-rt/lib/fuzzer/afl/afl_driver.cpp -O /fafuzz/afl_driver.cpp && \
    clang -Wno-pointer-sign -c /fafuzz/llvm_mode/afl-llvm-rt.o.c -I/fafuzz && \
    clang++ -stdlib=libc++ -std=c++11 -O2 -c /fafuzz/afl_driver.cpp && \
    ar r /libFAFUZZ.a *.o


#
#fairfuzz
#

#COPY afl-rb /fairfuzz

RUN cp -r /fuzzers/afl-rb /fairfuzz && \   
    cd /fairfuzz && \
#    git checkout e529c1f1b3666ad94e4d6e7ef24ea648aff39ae2 && \
    AFL_NO_X86=1 make

# Use afl_driver.cpp from LLVM as our fuzzing library.
RUN apt-get install wget -y && \
    wget https://raw.githubusercontent.com/llvm/llvm-project/5feb80e748924606531ba28c97fe65145c65372e/compiler-rt/lib/fuzzer/afl/afl_driver.cpp -O /fairfuzz/afl_driver.cpp && \
    clang -Wno-pointer-sign -c /fairfuzz/llvm_mode/afl-llvm-rt.o.c -I/fairfuzz && \
    clang++ -stdlib=libc++ -std=c++11 -O2 -c /fairfuzz/afl_driver.cpp && \
    ar r /libFAIRFUZZ.a *.o


#
#hastefuzz
#

# Download hastefuzz.
#COPY hastefuzz /hastefuzz
# Build hastefuzz without Python support as we don't need it.
# Set AFL_NO_X86 to skip flaky tests.
#RUN cp -r /fuzzers/hastefuzz /hastefuzz && \
#    cd /hastefuzz/fuzzer && \
#    unset CFLAGS CXXFLAGS && \
#    export CC=clang AFL_NO_X86=1 && \
#    PYTHON_INCLUDE=/ make && \
#    make install && \
#    cp utils/aflpp_driver/libAFLDriver.a /libHASTEFUZZ.a

#
#libfuzzer
#

ENV LF_PATH /tmp/libfuzzer.zip

# libFuzzer from branch llvmorg-15.0.3 with minor changes to build script.
RUN wget https://storage.googleapis.com/fuzzbench-artifacts/libfuzzer.zip -O $LF_PATH && \
    echo "ed761c02a98a16adf6bb9966bf9a3ffd6794367a29dd29d4944a5aae5dba3c90 $LF_PATH" | sha256sum --check --status && \
    mkdir /tmp/libfuzzer && \
    cd /tmp/libfuzzer && \
    unzip $LF_PATH  && \
    bash build.sh && \
    cp libFuzzer.a /usr/lib

#
#mopt 
#

#COPY MOpt-AFL /mopt

RUN cp -r /fuzzers/MOpt-AFL /mopt && \
    cd /mopt && \
    cd MOpt && AFL_NO_X86=1 make && \
    cp afl-fuzz ..

# Use afl_driver.cpp from LLVM as our fuzzing library.
RUN  cd /mopt/MOpt && \
    wget https://raw.githubusercontent.com/llvm/llvm-project/5feb80e748924606531ba28c97fe65145c65372e/compiler-rt/lib/fuzzer/afl/afl_driver.cpp -O /mopt/MOpt/afl_driver.cpp && \
    clang -Wno-pointer-sign -c -o /mopt/MOpt/afl-llvm-rt.o /mopt/MOpt/llvm_mode/afl-llvm-rt.o.c -I/mopt/MOpt && \
    clang++ -stdlib=libc++ -std=c++11 -O2 -c -o /mopt/MOpt/afl_driver.o /mopt/MOpt/afl_driver.cpp && \
    ar r /libMOPT.a *.o


#COPY wingfuzz wingfuzz

RUN cp -r /fuzzers/wingfuzz /wingfuzz && \
    cd /wingfuzz && \
    ./build.sh && cd instrument && ./build.sh && clang -c WeakSym.c && \
    cp ../libFuzzer.a /libWingfuzz.a && cp WeakSym.o / && cp LoadCmpTracer.so /

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

# Use afl_driver.cpp for AFL, and StandaloneFuzzTargetMain.c for Eclipser.
RUN wget https://raw.githubusercontent.com/llvm/llvm-project/5feb80e748924606531ba28c97fe65145c65372e/compiler-rt/lib/fuzzer/standalone/StandaloneFuzzTargetMain.c -O /StandaloneFuzzTargetMain.c && \
    clang -O2 -c /StandaloneFuzzTargetMain.c && \
    ar rc /libStandaloneFuzzTarget.a StandaloneFuzzTargetMain.o && \
    rm /StandaloneFuzzTargetMain.c


RUN cd /gmfuzzer &&\
    (for f in *.cpp; do \
      clang++ -stdlib=libc++ -fPIC -O2 -std=c++11 $f -c & \
    done && wait) && \
    ar r /usr/lib/libHCFUZZER.a *.o
