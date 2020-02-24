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

# Don't allow to call this scripts from its directory.
[ -e $(basename $0) ] && echo "DO NOT CALL THIS SCRIPT DIRECTLY" && exit 1

SCRIPT_DIR=$(dirname $0)
JOBS=${JOBS:-$(nproc)}

get_git_revision() {
  GIT_REPO="$1"
  GIT_REVISION="$2"
  TO_DIR="$3"

  if [ ! -e $TO_DIR ]; then
    git clone $GIT_REPO $TO_DIR
    (cd $TO_DIR && git reset --hard $GIT_REVISION)
  fi
}

get_git_tag() {
  GIT_REPO="$1"
  GIT_TAG="$2"
  TO_DIR="$3"

  if [ ! -e $TO_DIR ]; then
    git clone $GIT_REPO $TO_DIR
    (cd $TO_DIR && git checkout $GIT_TAG)
  fi
}

get_svn_revision() {
  SVN_REPO="$1"
  SVN_REVISION="$2"
  TO_DIR="$3"

  if [ ! -e $TO_DIR ]; then
    svn co -r$SVN_REVISION $SVN_REPO $TO_DIR
  fi
}
