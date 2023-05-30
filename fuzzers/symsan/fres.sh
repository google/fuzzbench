#!/bin/bash

# Copyright 2021 Google LLC
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

# avoid coredumps since they take up hundreds of GBs of disk space
ulimit -S -c 0
ulimit -H -c 0
RUST_BACKTRACE=1 RUST_LOG=info /out/run_with_multilog.sh /out/corpus/.log_res /out/fastgen --sync_afl -i - -o /out/corpus -t $1 -- $2 @@
