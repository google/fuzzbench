# Copyright 2019 Google Inc.
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

RUN apt-get update && apt-get upgrade -y && apt-get install -y pkg-config wget

RUN git clone \
        --depth 1 \
        --branch rel-0.60.8 \
        https://github.com/gnuaspell/aspell.git \
        $SRC/aspell

RUN git clone \
        https://github.com/gnuaspell/aspell-fuzz.git \
        $SRC/aspell-fuzz

# Suppress an immediate UBSan violation that prevents fuzzing
RUN wget https://github.com/GNUAspell/aspell/commit/a2cd7ffd25e6213f36139cda4a911e2e03ed417c.patch -O $SRC/aspell/fix_aspell_ub.patch

WORKDIR $SRC/aspell-fuzz
COPY build.sh $SRC/

