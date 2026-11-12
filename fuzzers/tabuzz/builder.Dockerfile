ARG parent_image
FROM $parent_image

RUN apt-get update && \
    apt-get install -y git make clang llvm

RUN git clone https://github.com/AFLplusplus/AFLplusplus /aflplusplus
RUN cd /aflplusplus && make source-only

RUN git clone https://github.com/135204660/tabuzz-mutator.git /tabuzz
RUN cd /tabuzz && \
    gcc -shared -fPIC -I /aflplusplus/include -o tabuzz_mutator.so tabuzz_mutator.c

RUN cp /aflplusplus/afl-compiler-rt.o /fuzzer_lib.a
ENV FUZZER_LIB=/fuzzer_lib.a
