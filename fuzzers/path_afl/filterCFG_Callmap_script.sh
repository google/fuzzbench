#!/bin/bash

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

# 获取 PUT 的反汇编结果
objdump -d path_to_put > PUT_decomp.txt

# 运行过滤CFG python 脚本
python3 filterCFG.py cfg.txt PUT_decomp.txt cfg_filtered.txt

# 运行过滤Callmap python 脚本
python3 filterCallmap.py cfg_filtered.txt callmap.txt callmap_filtered.txt

