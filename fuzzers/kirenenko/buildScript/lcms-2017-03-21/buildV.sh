#!/bin/bash -ex
# Copyright 2020 Google LLC
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

cd Little-CMS
#git checkout f9d75ccef0b54c9f4167d95088d4727985133c52
make clean
./autogen.sh
./configure
make -j $(nproc)


$CC $CFLAGS /buildScript/standaloneengine.c /buildScript/lcms-2017-03-21/cms_transform_fuzzer.c -I include/ src/.libs/liblcms2.a \
     -o $OUT/cms_transform_fuzzer_vani
#cp -r /opt/seeds $OUT/
#cp -r /opt/seeds $OUT/
