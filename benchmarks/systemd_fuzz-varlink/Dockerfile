# syntax=docker/dockerfile:1.3-labs
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

FROM gcr.io/oss-fuzz-base/base-builder@sha256:fb1a9a49752c9e504687448d1f1a048ec1e062e2e40f7e8a23e86b63ff3dad7c

RUN apt-get update && \
    apt-get install -y libcap-dev \
        gperf m4 gettext  libmount-dev libkmod-dev pkg-config wget \
        ninja-build=1.10.0-1build1 && \
    pip3 install meson==0.55.3

RUN git clone https://github.com/systemd/systemd && \
    git -C "$SRC/systemd" checkout cb367b17853d215ebcf2816118c1f53d003e5088 && \
    cp $SRC/systemd/tools/oss-fuzz.sh $SRC/build.sh

# Some fixes to make the old version build & run.
# Fix ninja version compatibility error.
ENV PATH='/usr/bin':$PATH
# Remove a buggy lines that zip corpus files that do not exist.
RUN sed -i '37,42d' $SRC/build.sh && \
    # Copy shared lib and patch rpath so that they can be found in the runner.
    cat >> "$SRC/build.sh" <<'EOF'
for lib_path in $(ldd "$OUT"/src/shared/libsystemd-shared-*.so \
    | perl -lne 'print $1 if m{=>\s+(/lib\S+)}'); do
    lib_name=$(basename "$lib_path")
    cp "$lib_path" "$OUT/src/shared"
    patchelf --set-rpath \$ORIGIN "$OUT/src/shared/$lib_name"
done
patchelf --set-rpath \$ORIGIN "$OUT"/src/shared/libsystemd-shared-*.so
EOF

WORKDIR systemd
