#ifndef LOG_COLLECT_H
#define LOG_COLLECT_H
#include <stdint.h>
#ifdef __cplusplus
extern "C"{
#endif

  void __angora_log_collect_cmp(uint32_t cmpid, uint32_t context, uint32_t pcid, uint32_t condition, uint32_t level,
                                uint32_t op, uint32_t size,  uint32_t lb1, uint32_t lb2,  uint64_t arg1, uint64_t arg2);

  void __angora_log_collect_fini();

#ifdef __cplusplus
}
#endif

#endif
