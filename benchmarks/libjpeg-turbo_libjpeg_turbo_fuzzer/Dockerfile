# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
################################################################################

FROM gcr.io/oss-fuzz-base/base-builder@sha256:87ca1e9e19235e731fac8de8d1892ebe8d55caf18e7aa131346fc582a2034fdd

RUN apt-get update && \
    apt-get install -y make yasm cmake

RUN git clone https://github.com/libjpeg-turbo/fuzz && \
    cat fuzz/branches.txt | while read branch; do \
      git clone https://github.com/libjpeg-turbo/libjpeg-turbo \
          -b $branch libjpeg-turbo.$branch; \
    done

RUN git clone https://github.com/libjpeg-turbo/seed-corpora && \
    git -C seed-corpora checkout 7c9ea5ffaac76ef618657978c9fdfa845d310b93
RUN cd seed-corpora && \
    zip -r ../decompress_fuzzer_seed_corpus.zip \
        afl-testcases/jpeg* \
        bugs/decompress* \
        $SRC/libjpeg-turbo/testimages/*.jpg
RUN cd seed-corpora && \
    zip -r ../compress_fuzzer_seed_corpus.zip \
        afl-testcases/bmp \
        afl-testcases/gif* \
        bugs/compress* \
        $SRC/libjpeg-turbo/testimages/*.bmp \
        $SRC/libjpeg-turbo/testimages/*.ppm
RUN rm -rf seed-corpora

COPY build.sh $SRC/
