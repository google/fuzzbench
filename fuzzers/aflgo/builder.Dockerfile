ARG parent_image

FROM $parent_image


#RUN apt-get update

RUN git clone https://github.com/aflgo/aflgo.git /afl

RUN cd /afl && \
    git checkout cd9bca7e4cba9038f6e7e81f3938f379c754fc5a && \
    INITIAL_CXXFLAGS=$CXXFLAGS && \
    INITIAL_CFLAGS=$CFLAGS && \
    unset CFLAGS CXXFLAGS && \
    scripts/build/aflgo-build.sh && \
    CXXFLAGS=$INITIAL_CXXFLAGS && \
    CFLAGS=$INITIAL_CFLAGS


RUN apt-get update && \
    apt-get install wget -y && \
    wget https://raw.githubusercontent.com/llvm/llvm-project/5feb80e748924606531ba28c97fe65145c65372e/compiler-rt/lib/fuzzer/afl/afl_driver.cpp -O /afl/afl_driver.cpp && \
    clang++ -stdlib=libc++ -std=c++11 -O2 -c /afl/afl_driver.cpp && \
    ar r /libAFL.a *.o
