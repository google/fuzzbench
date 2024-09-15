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

FROM gcr.io/oss-fuzz-base/base-builder@sha256:87ca1e9e19235e731fac8de8d1892ebe8d55caf18e7aa131346fc582a2034fdd

RUN git clone \
        https://github.com/gnuaspell/aspell.git \
        $SRC/aspell

RUN git clone \
        https://github.com/gnuaspell/aspell-fuzz.git \
        $SRC/aspell-fuzz && \
    git -C $SRC/aspell-fuzz checkout fa4aa32c6bf9573801a7675137e1c31b9f13247f


WORKDIR $SRC/aspell-fuzz
COPY build.sh $SRC/

