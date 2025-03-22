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

FROM gcr.io/oss-fuzz-base/base-builder@sha256:87ca1e9e19235e731fac8de8d1892ebe8d55caf18e7aa131346fc582a2034fdd

RUN apt-get update && \
    apt-get install -y \
        libstdc++-9-dev libstdc++-9-dev:i386 nasm subversion \
        gnupg lsb-release software-properties-common pkg-config \
        python3-pip libgtk-3-dev unzip pax-utils file cpio ninja-build cmake \
        libgcrypt20-dev libc-ares-dev libpcre2-dev flex inotify-tools \
        libboost-dev 

RUN git clone \
        https://gitlab.com/wireshark/wireshark

WORKDIR wireshark
COPY build.sh $SRC/
