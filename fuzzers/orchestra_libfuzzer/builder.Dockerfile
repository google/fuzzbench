ARG parent_image
FROM $parent_image

#
# AFLplusplus
#

RUN apt-get update && \
    apt-get install -y \
        wget
        
RUN git clone -b master https://github.com/gtt1995/GMFuzzer.git /gmfuzzer
RUN git clone -b fuzzers https://github.com/gtt1995/GMFuzzer.git /fuzzers

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

RUN cd /gmfuzzer &&\
    (for f in *.cpp; do \
      clang++ -stdlib=libc++ -fPIC -O2 -std=c++11 $f -c & \
    done && wait) && \
    ar r /usr/lib/libHCFUZZER.a *.o
