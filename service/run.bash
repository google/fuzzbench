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

# Use this script to clone a new copy of fuzzbench and run a requested
# experiment.

# Append stdout and stderr to /tmp/fuzzbench-service.logs. Redirecting the
# stdout/stderr of this script in the cron command didn't work for some reason.
exec &>> /tmp/fuzzbench-service.logs

# Use a seperate working directory to run the experiment so we don't pollute
# the source code with the config directory created by run_experiment.py
experiment_working_dir=/tmp/fuzzbench-automatic-experiment-working-dir

repo_path=/tmp/fuzzbench-automatic-experiment-repo
rm -rf $repo_path $experiment_working_dir

mkdir $experiment_working_dir

git clone https://github.com/google/fuzzbench.git $repo_path
cd $repo_path

make install-dependencies
source .venv/bin/activate
export PYTHONPATH=$repo_path

cd $experiment_working_dir
python3 $repo_path/service/automatic_run_experiment.py
rm -rf $repo_path
