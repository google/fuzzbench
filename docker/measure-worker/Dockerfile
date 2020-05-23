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

ENV WORK /work
WORKDIR $WORK

ENV VIRTUALENV_DIR $WORK/.venv

RUN mkdir -p /work && virtualenv --python=$(which python3) $VIRTUALENV_DIR

ENV SRC $WORK/src

# Copy requirements.txt and install dependencies before copying all of the
# source code so the cache hits more often.
COPY requirements.txt $SRC/
ENV PYTHONPATH=$SRC
RUN /bin/bash -c "source $VIRTUALENV_DIR/bin/activate && \
    pip3 install -r $SRC/requirements.txt"

ADD . $SRC/

ENTRYPOINT /bin/bash $SRC/docker/measure-worker/startup-worker.sh
