#!/bin/bash
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

test -z "$1" -o -z "$2" -o '!' -e "$1" && exit 0

file "$1" | grep -q executable && {
  nm "$1" | grep -i "T $2" | awk '{print"0x"$1}'
  exit 0
}

nm "$1" | grep -i "T $2" | '{print$1}' | tr a-f A-F | \
  xargs echo "ibase=16;obase=10;555555554000 + " | bc | tr A-F a-f
exit 0
