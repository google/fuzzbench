# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

ARG parent_image
FROM $parent_image

# Install the necessary packages.
RUN apt-get update && \
    apt-get install -y wget libstdc++-5-dev libtool-bin automake flex bison \
                       libglib2.0-dev libpixman-1-dev python3-setuptools unzip

RUN curl -fsSL https://deb.nodesource.com/setup_lts.x | bash -
RUN apt-get install -y nodejs

# Download afl++
RUN git clone https://github.com/WorksButNotTested/AFLplusplus.git /afl && \
    cd /afl && git checkout 6e373f0ade220d320d2d452e099a786dff9f3cd0

# Build afl++ without Python support as we don't need it.
# Set AFL_NO_X86 to skip flaky tests.
RUN cd /afl && \
    unset CFLAGS && unset CXXFLAGS && \
    AFL_NO_X86=1 CC=clang PYTHON_INCLUDE=/ make && \
    make -C utils/aflpp_driver && \
    cd frida_mode && make FRIDA_SOURCE=1 && cd .. && \
    cp utils/aflpp_driver/libAFLQemuDriver.a /libAFLDriver.a

RUN cd /afl/frida_mode/build/frida-source/frida-gum && \
    git remote add private https://github.com/WorksButNotTested/frida-gum.git && \
    git fetch -a private && \
    git checkout adac9cd509afd9b3b468ba95e949f4810a1385e3

RUN cd /afl/frida_mode && \
    make FRIDA_SOURCE=1

COPY get_frida_entry.sh /
