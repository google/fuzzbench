# Copyright 2016 Google Inc.
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

RUN apt-get update && \
    apt-get install -y \
        make autoconf automake libtool g++ sqlite3 pkg-config wget

RUN git clone \
        --depth 1 \
        --branch 9.1.0 \
        https://github.com/OSGeo/PROJ \
        PROJ
RUN git clone \
        --depth 1 \
        --branch curl-7_86_0 \
        https://github.com/curl/curl.git \
        PROJ/curl
# Use a commit hash instead of the latest release of libtiff because the latter
# does not use autogen.sh, which is required in the lateest build.sh.
# Feel free to change back to release tag in the next update.
RUN git clone \
        https://gitlab.com/libtiff/libtiff.git \
        PROJ/libtiff && \
    (cd PROJ/libtiff && \
    git checkout 31d9e9f73dc8b6fa599c931d9ff058d8ea32795c)

WORKDIR PROJ

RUN cp test/fuzzers/build.sh $SRC/
# This is to fix Fuzz Introspector build by using LLVM old pass manager
# re https://github.com/ossf/fuzz-introspector/issues/305
ENV OLD_LLVMPASS 1
ENV fuzzerName=standard_fuzzer
