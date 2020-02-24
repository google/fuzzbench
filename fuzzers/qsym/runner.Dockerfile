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

FROM gcr.io/fuzzbench/base-runner

# Install compilers and sudo needed by QSYM's build scripts.
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    sudo

# Finally, clone the source for QSYM and build it.
# Remove ptrace_scope check in setup.*. This cannot be enabled in Google Cloud
# build, but it is enabled at runtime on the bot.
RUN git clone https://github.com/sslab-gatech/qsym.git qsym && \
    cd qsym && \
    git checkout 3fe575cab73e1ccd80ae2605ca08999f7ddbd437 && \
    sed -i '3,7d' ./setup.sh && \
    sed -i '23,25d' ./setup.py && \
    sed -i 's/pytest-xdist//g' setup.py && \
    ./setup.sh && \
    pip install .
