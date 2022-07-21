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

FROM gcr.io/oss-fuzz-base/base-builder@sha256:c0eeba3437a2173c6a7115cf43062b351ed48cc2b54f54f895423d6a5af1dc3e
ADD bionic.list /etc/apt/sources.list.d/bionic.list
ADD nasm_apt.pin /etc/apt/preferences
RUN apt-get update && apt-get upgrade -y && apt-get install -y make autoconf automake libtool build-essential \
    libass-dev libfreetype6-dev libsdl1.2-dev \
    libvdpau-dev libxcb1-dev libxcb-shm0-dev \
    pkg-config texinfo libbz2-dev zlib1g-dev yasm cmake mercurial wget \
    xutils-dev libpciaccess-dev nasm

RUN git clone https://git.ffmpeg.org/ffmpeg.git ffmpeg

RUN wget https://www.alsa-project.org/files/pub/lib/alsa-lib-1.1.0.tar.bz2
RUN git clone -n https://gitlab.freedesktop.org/mesa/drm.git
RUN cd drm; git checkout 5db0f7692d1fdf05f9f6c0c02ffa5a5f4379c1f3 
RUN git clone --depth 1 https://github.com/mstorsjo/fdk-aac.git
ADD https://sourceforge.net/projects/lame/files/latest/download lame.tar.gz
RUN git clone --depth 2 git://anongit.freedesktop.org/xorg/lib/libXext
RUN (cd /src/libXext; git checkout d965a1a8ce9331d2aaf1c697a29455ad55171b36)
RUN git clone -n git://anongit.freedesktop.org/git/xorg/lib/libXfixes
RUN cd libXfixes; git checkout 174a94975af710247719310cfc53bd13e1f3b44d
RUN git clone --depth 1 https://github.com/intel/libva
RUN git clone --depth 1 -b libvdpau-1.2 git://people.freedesktop.org/~aplattner/libvdpau
RUN git clone --depth 1 https://chromium.googlesource.com/webm/libvpx
RUN git clone --depth 1 https://github.com/xiph/ogg
RUN git clone --depth 1 https://github.com/xiph/opus
RUN git clone --depth 1 https://github.com/xiph/theora
RUN git clone --depth 1 https://github.com/xiph/vorbis
RUN git clone --depth 1 https://code.videolan.org/videolan/x264.git
RUN git clone --depth 1 https://bitbucket.org/multicoreware/x265_git.git
RUN mv x265_git x265

COPY build.sh group_seed_corpus.py $SRC/
