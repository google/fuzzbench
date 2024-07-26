#ifndef UTIL_H_
#define UTIL_H_
void generate_input(std::unordered_map<uint32_t,uint8_t> &sol, std::string taint_file, std::string outputDir, uint32_t fid);
// void generate_PC_set(const char *smt2str, uint32_t inputid, uint32_t outputid, int isNested);
uint32_t load_input(std::string taint_file, unsigned char* input);
uint64_t getTimeStamp();
#endif
