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

FROM gcr.io/oss-fuzz-base/base-builder@sha256:87ca1e9e19235e731fac8de8d1892ebe8d55caf18e7aa131346fc582a2034fdd

RUN apt-get update && \
    apt-get install -y \
        make \
        autoconf \
        libtool \
        build-essential \
        libass-dev \
        libfreetype6-dev \
        libsdl1.2-dev \
        libvdpau-dev \
        libxcb1-dev \
        libxcb-shm0-dev \
        libdrm-dev \
        pkg-config \
        texinfo \
        libbz2-dev \
        zlib1g-dev \
        yasm \
        cmake \
        mercurial \
        wget \
        xutils-dev \
        libpciaccess-dev \
        nasm \
        meson \
        rsync && \
    curl \
        -LO \
        http://mirrors.kernel.org/ubuntu/pool/main/a/automake-1.16/automake_1.16.5-1.3_all.deb && \
    apt install ./automake_1.16.5-1.3_all.deb && \
    rm automake_1.16.5-1.3_all.deb

RUN git clone \
        --branch v1.2.8 \
        --depth 1 \
        https://github.com/alsa-project/alsa-lib.git

RUN git clone \
        --branch v2.0.2 \
        --depth 1 \
        https://github.com/mstorsjo/fdk-aac.git

RUN git clone \
        --branch libXext-1.3.5 \
        --depth 1 \
        https://gitlab.freedesktop.org/xorg/lib/libxext.git

RUN git clone \
        --depth 1 \
        --branch 2.16.0 \
        https://github.com/intel/libva

RUN git clone \
        --depth 1 \
        --branch libvdpau-1.2 \
        https://gitlab.freedesktop.org/vdpau/libvdpau.git

RUN git clone \
        --depth 1 \
        --branch v1.12.0 \
        https://chromium.googlesource.com/webm/libvpx

RUN git clone \
    --depth 1 \
    --branch v1.3.5 \
    https://github.com/xiph/ogg

RUN git clone \
        --depth 1 \
        --branch v1.3.1 \
        https://github.com/xiph/opus

RUN git clone \
        --depth 1 \
        --branch v1.1.1 \
        https://github.com/xiph/theora

RUN git clone \
        --depth 1 \
        --branch v1.3.7 \
        https://github.com/xiph/vorbis

RUN git clone \
        --depth 1 \
        --branch v2.10.3 \
        https://gitlab.gnome.org/GNOME/libxml2.git

RUN git clone \
        --branch n5.1.2 \
        --depth 1 \
        https://git.ffmpeg.org/ffmpeg.git

COPY build.sh group_seed_corpus.py $SRC/
