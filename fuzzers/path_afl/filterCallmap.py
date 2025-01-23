import sys
import re

# 检查是否传入了足够的参数（至少需要三个参数加上脚本名称）
assert(len(sys.argv) == 4)
# 打印第一个、第二个和第三个参数
# python3 filterCallmap.py cfg_filtered.txt callmap.txt callmap_filtered.txt
# print(f"参数1: {sys.argv[1]}")
# print(f"参数2: {sys.argv[2]}")
# print(f"参数3: {sys.argv[3]}")

# 思考代码：
# 1.读取 cfg_filtered.txt，扫描每个 BasicBlock，记录它们的编号，存到一个字典里
# 2.读取 callmap.txt 的每一行，根据读到的 BBID 去比较字典里是否存在这个 BBID，来决定是否把这行输出到 callmap_filtered.txt 里

# 1.读取 cfg_filtered.txt，扫描每个 BasicBlock，记录它们的编号，存到一个字典里
bbdict = {}
with open(sys.argv[1], 'r', encoding='utf-8') as file:
    for line in file:
        # 使用 strip() 去除每行末尾的换行符
        line = line.strip()
        BasicBlock_match = re.search(r'BasicBlock: (\d+)', line)
        if BasicBlock_match:
            bbid = int(BasicBlock_match.group(1))
            bbdict[bbid] = 1
        else:
            # 如果这行不包含 "BasicBlock"，那么不做任何事情
            pass

# 2.读取 callmap.txt 的每一行，根据读到的 BBID 去比较字典里是否存在这个 BBID，来决定是否把这行输出到 callmap_filtered.txt 里
written_file = open(sys.argv[3], 'w')
with open(sys.argv[2], 'r', encoding='utf-8') as file:
    for line in file:
        # 使用 strip() 去除每行末尾的换行符
        line = line.strip()
        bbid_match = re.search(r'(\d+).*', line)
        bbid = int(bbid_match.group(1))
        if bbid in bbdict:
            written_file.write(line + "\n")

