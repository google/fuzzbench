#! /usr/bin/env bash
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
#

SRC_DIR=$1

tar xf libpastis.tar.gz
cd libpastis
pip3 install .
cd ..

tar xf klockwork.tar.gz
cd klockwork
pip3 install .
cd ..

tar xf pastis-aflpp.tar.gz
cd pastis-aflpp
pip3 install .
cd broker-addon/
pip3 install .
cd ../..

tar xf pastis-hf.tar.gz
cd pastis-hf
pip3 install .
cd broker-addon/
pip3 install .
cd ../..

tar xf tritondse.tar.gz
cd tritondse
pip3 install .
cd ..

tar xf pastis-triton.tar.gz
cd pastis-triton
pip3 install .
cd broker-addon/
pip3 install .
cd ../..

tar xf pastis-broker.tar.gz
cd pastis-broker
pip3 install .
cd ..

tar xf pastisd.tar.gz
cd pastisd/
pip3 install .
cd ..

tar xf pastis-benchmarks.tar.gz
cd pastis-benchmarks/
pip3 install .
cd ..
