FROM gcr.io/oss-fuzz-base/base-builder

# Install necessary dependencies
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y \
    make \
    autoconf \
    libtool \
    wget

# Clone necessary repositories
RUN git clone git://git.sv.nongnu.org/freetype/freetype2.git $SRC/freetype2
RUN git clone https://github.com/unicode-org/text-rendering-tests.git $SRC/TRT
RUN wget https://github.com/libarchive/libarchive/releases/download/v3.4.3/libarchive-3.4.3.tar.xz -P $SRC/

# Copy all files into $SRC directory
COPY * $SRC/

# Download and extract the seeds tarball into $SRC/seeds
RUN wget https://raw.githubusercontent.com/ardier/fuzzbench/minimized-subsumed-mutants-benchmark-with-seeds/benchmarks/freetype2_ftfuzzer_libafl/seeds.tar -O $SRC/seeds.tar && \
    mkdir -p $SRC/seeds && \
    tar -xvf $SRC/seeds.tar -C $SRC/seeds && \
    rm $SRC/seeds.tar

# Clean up temporary files
RUN mkdir -p $SRC/corpus
ENV FUZZER_SEEDS="$SRC/seeds"
ENV FUZZER_CORPUS="$SRC/corpus"
