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
    apt-get install -y \
    make \
    automake \
    autoconf \
    libtool \
    wget

RUN git clone https://github.com/xiph/ogg.git && \
    git -C ogg checkout db5c7a49ce7ebda47b15b78471e78fb7f2483e22
RUN git clone https://github.com/xiph/vorbis.git
RUN wget -qO $SRC/decode_fuzzer.cc \
    https://raw.githubusercontent.com/google/oss-fuzz/688aadaf44499ddada755562109e5ca5eb3c5662/projects/vorbis/decode_fuzzer.cc

COPY build.sh $SRC/
ADD seeds /opt/seeds
