# Copyright 2023 Google LLC
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

FROM gcr.io/cloud-builders/gcloud

RUN apt-get update && apt-get install python3-pip -y

# Do this expensive step before the cache is destroyed.
RUN pip install pip --upgrade
COPY ./requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt
RUN pip install PyGithub==1.51

ENV FUZZBENCH_DIR /opt/fuzzbench
COPY . $FUZZBENCH_DIR

WORKDIR $FUZZBENCH_DIR
ENV PYTHONPATH=$FUZZBENCH_DIR
ENV FORCE_LOCAL=1
ENTRYPOINT ["python3", "/opt/fuzzbench/service/gcbrun_experiment.py"]