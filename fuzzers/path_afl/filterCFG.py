import sys
import re

# 检查是否传入了足够的参数（至少需要三个参数加上脚本名称）
assert(len(sys.argv) == 4)
# 打印第一个、第二个和第三个参数
# python3 filterCFG.py cfg.txt PUT_decomp.txt cfg_filtered.txt
print(f"参数1: {sys.argv[1]}")
print(f"参数2: {sys.argv[2]}")
print(f"参数3: {sys.argv[3]}")

# 思考代码：
# 1.先把整个 cfg.txt 读入内存，按照 {key="第一个基本块的块号", value=[bool: false, "CFG字符串列表"]} 来储存
# 2.扫描反汇编代码，扫描每个函数
#     1.如果函数中没有对 path_inject_eachbb 的调用，那说明不是 PUT 源码，下一个函数
#     2.如果有，那么看第一个 path_inject_eachbb 的参数，随后使用这个参数索引到之前的字典
#       把字典 value 里对应的 false 设置为 true，随后继续下一个函数，直到扫描完整个反汇编文件
# 3.扫描一遍之前的字典，把所有 bool = true 的 CFG字符串列表 dump 到 cfg_filtered.txt 里

# 1.先把整个 cfg.txt 读入内存，按照 {key="第一个基本块的块号", value=[bool: false, "CFG字符串列表"]} 来储存
justEnterFunction = False # 这个flag用来识别每个函数的第一个基本块 entrypoing
with open(sys.argv[1], 'r', encoding='utf-8') as file:
    wholeCFG = {}
    singleCFG = []
    firstBBID = -1
    for line in file:
        # 使用 strip() 去除每行末尾的换行符
        line = line.strip()
        if "Function: " in line:
            # 如果 singleCFG 不为空，那么把它放进 wholeCFG 字典里
            if singleCFG:
                wholeCFG[firstBBID] = [False, singleCFG]
            singleCFG = []
            justEnterFunction = True
        else:
            if justEnterFunction:
                match = re.search(r'BasicBlock: (\d+)', line)
                assert(match)
                justEnterFunction = False
                firstBBID = int(match.group(1))
            else:
                pass
                # do nothing
        singleCFG.append(line)
    file.close()

# 循环结束后，还有最后一个函数的 CFG 没有加入 wholeCFG，现在加进去
wholeCFG[firstBBID] = [False, singleCFG]

# 2.扫描反汇编代码，扫描每个函数
#     1.如果函数中没有对 path_inject_eachbb 的调用，那说明不是 PUT 源码，下一个函数
#     2.如果有，那么看第一个 path_inject_eachbb 的参数，随后使用这个参数索引到之前的字典
#       把字典 value 里对应的 false 设置为 true，随后继续下一个函数，直到扫描完整个反汇编文件
justEnterFunction = False # 这个flag用来识别是否在一个函数内
with open(sys.argv[2], 'r', encoding='utf-8') as file:
    for line in file:
        # 使用 strip() 去除每行末尾的换行符
        line = line.strip()
        funcNameMatch = re.match(r'^[0-9a-fA-F]+ <[^>]+>:', line)
        if funcNameMatch:
            # if justEnterFunction: 
                # 若此时 justEnterFunction = True，说明上一个函数中不包含 callq path_inject_eachbb，不做处理直接skip
                # 若此时 justEnterFunction = False，说明上一个函数中包含 callq path_inject_eachbb 已被找到，不做处理直接skip
            justEnterFunction = True
        elif justEnterFunction:
            path_inject_match = re.search(r'call?\s+[0-9a-fA-F]+\s+<path_inject_eachbb>', line)
            if path_inject_match:
                # 到这里已经找到这个函数的第一个 callq path_inject_eachbb 了，除了重置 justEnterFunction，
                # 还要对 step1 里得到的字典做相应的处理
                # 此时，previousline 有两种可能：
                #     1. xor    %edi,%edi
                #     2. mov    $0x3208,%edi
                print('matched!')
                xor_match = re.search(r'xor\s+%edi,%edi', previousline)
                mov_match = re.search(r'mov\s+\$(0x[0-9a-fA-F]+),%edi', previousline)
                assert(xor_match or mov_match)
                assert(not (xor_match and mov_match))
                if xor_match:
                    # 如果 previousline = xor 汇编指令，path_inject_eachbb 的参数是 0
                    arg = 0
                else:
                    arg = int(mov_match.group(1), 16)
                print(f"arg: {arg} {mov_match.group(1)}")
                wholeCFG[arg][0] = True
                justEnterFunction = False
            else:
                # 如果在函数里还有没有遇到 callq path_inject_eachbb，那么就继续读下一行
                pass
        else:
            # 如果既没有匹配到函数头，justEnterFunction = False
            # 说明这个函数的 第一个callq path_inject_eachbb 已经被找到了
            # 继续下一行文字，直到进入到下一个函数为止
            pass
        # 记录当前行，这一行的目的是在找到 callq path_inject_eachbb 后，寻找这个函数的参数
        previousline = line
    file.close()

# # 打印 wholeCFG
# print(wholeCFG)

# 3.扫描一遍之前的字典，把所有 bool = true 的 CFG字符串列表 dump 到 cfg_filtered.txt 里
# 打开文件以写入模式（'w'）
with open(sys.argv[3], "w") as file:
    for key, value in wholeCFG.items():
        if value[0]:
            for line in value[1]:
                file.write(line + "\n")
    file.close()


# xor    %esi,%esi
#   2038f6:       bf 08 32 00 00          mov    $0x3208,%edi
#   2038fb:       e8 a0 e4 e0 00          callq  1011da0 <path_inject_eachbb>






