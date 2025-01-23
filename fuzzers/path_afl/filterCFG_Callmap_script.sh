#!/bin/bash

# 获取 PUT 的反汇编结果
objdump -d path_to_put > PUT_decomp.txt

# 运行过滤CFG python 脚本
python3 filterCFG.py cfg.txt PUT_decomp.txt cfg_filtered.txt

# 运行过滤Callmap python 脚本
python3 filterCallmap.py cfg_filtered.txt callmap.txt callmap_filtered.txt

