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

RUN git clone https://github.com/WingTecherTHU/wingfuzz
RUN cd wingfuzz && git checkout 6ef3281f145fa1839df0f46c38b348ec9d93b0e2 && \
    ./build.sh && cd instrument && ./build.sh && clang -c WeakSym.c && \
    cp ../libFuzzer.a /libWingfuzz.a && cp WeakSym.o / && cp LoadCmpTracer.so /
