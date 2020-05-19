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

# OSS-Fuzz sets the environment variables CC/CXX/CFLAGS/CXXFLAGS. These cannot
# be deleted from the environment because of the way docker works. Instead we
# will set them to reasonable values for FuzzBench. These flags will probably
# only be used for compiling fuzzers in their builder.Dockerfiles.
ENV CC="clang"
ENV CXX="clang++"

ENV CFLAGS="-O3"
ENV CXXFLAGS="-O3 -stlib=libc++"

# TODO(metzman): Change this to copy Python3.7 from base-image.
RUN apt-get update -y && apt-get install -y python3

# TODO(metzman): Install dependencies from base-image and base-builder.