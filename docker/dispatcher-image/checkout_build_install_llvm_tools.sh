#!/bin/bash -eux
# Copyright 2016 Google Inc.
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

LLVM_DEP_PACKAGES="build-essential make cmake ninja-build git python2.7 g++-multilib"
apt-get install -y $LLVM_DEP_PACKAGES

# Checkout
CHECKOUT_RETRIES=10
function clone_with_retries {
  REPOSITORY=$1
  LOCAL_PATH=$2
  CHECKOUT_RETURN_CODE=1

  # Disable exit on error since we might encounter some failures while retrying.
  set +e
  for i in $(seq 1 $CHECKOUT_RETRIES); do
    rm -rf $LOCAL_PATH
    git clone $REPOSITORY $LOCAL_PATH
    CHECKOUT_RETURN_CODE=$?
    if [ $CHECKOUT_RETURN_CODE -eq 0 ]; then
      break
    fi
  done

  # Re-enable exit on error. If checkout failed, script will exit.
  set -e
  return $CHECKOUT_RETURN_CODE
}

# Use chromium's clang revision
mkdir $SRC/chromium_tools
cd $SRC/chromium_tools
git clone https://chromium.googlesource.com/chromium/src/tools/clang
cd clang

LLVM_SRC=$SRC/llvm-project

# For manual bumping.
OUR_LLVM_REVISION=e84b7a5fe230e42b8e6fe451369874a773bf1867

# To allow for manual downgrades. Set to 0 to use Chrome's clang version (i.e.
# *not* force a manual downgrade). Set to 1 to force a manual downgrade.
FORCE_OUR_REVISION=0
LLVM_REVISION=$(grep -Po "CLANG_REVISION = '\K[a-f0-9]+(?=')" scripts/update.py)

clone_with_retries https://github.com/llvm/llvm-project.git $LLVM_SRC

set +e
git -C $LLVM_SRC merge-base --is-ancestor $OUR_LLVM_REVISION $LLVM_REVISION
IS_OUR_REVISION_ANCESTOR_RETCODE=$?
set -e

# Use our revision if specified by FORCE_OUR_REVISION or if our revision is a
# later revision than Chrome's (i.e. not an ancestor of Chrome's).
if [ $IS_OUR_REVISION_ANCESTOR_RETCODE -ne 0 ] || [ $FORCE_OUR_REVISION -eq 1 ] ; then
  LLVM_REVISION=$OUR_LLVM_REVISION
fi

git -C $LLVM_SRC checkout $LLVM_REVISION
echo "Using LLVM revision: $LLVM_REVISION"

# Build & Install.
mkdir -p $WORK/llvm-builddir
cd $WORK/llvm-builddir

cmake $LLVM_SRC/llvm
make llvm-profdata llvm-cov
make install-llvm-profdata
make install-llvm-cov

# Clean up
rm -rf $WORK/llvm-builddir
rm -rf $LLVM_SRC
rm -rf $SRC/chromium_tools
