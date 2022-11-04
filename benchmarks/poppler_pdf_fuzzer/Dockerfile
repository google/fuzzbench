# Copyright 2018 Google Inc.
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

FROM gcr.io/oss-fuzz-base/base-builder@sha256:fb1a9a49752c9e504687448d1f1a048ec1e062e2e40f7e8a23e86b63ff3dad7c
MAINTAINER jonathan@titanous.com
RUN apt-get update && apt-get upgrade -y && apt-get install -y make autoconf libz-dev lib32z1-dev zlib1g-dev automake libtool pkg-config cmake
RUN git clone \
        --depth 1 \
        --branch poppler-22.11.0 \
        https://github.com/freedesktop/poppler.git
RUN git clone \
        --depth 1 \
        --branch VER-2-12-1 \
        https://gitlab.freedesktop.org/freetype/freetype.git
RUN git clone \
        --depth 1 \
        --branch v3.0.279 \
        https://github.com/mozilla/pdf.js pdf.js && \
    zip -q $SRC/pdf_fuzzer_seed_corpus.zip pdf.js/test/pdfs/*.pdf && \
    rm -rf pdf.js
ADD https://raw.githubusercontent.com/rc0r/afl-fuzz/master/dictionaries/pdf.dict $SRC/pdf_fuzzer.dict
WORKDIR $SRC
COPY *.cc poppler/fuzz/
COPY build.sh $SRC/
