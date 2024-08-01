
#include "stdint.h"

// uint32_t __angora_cond_cmpid;
// void __angora_set_cmpid(uint32_t id) { __angora_cond_cmpid = id; }

extern __thread uint32_t __angora_prev_loc;
extern __thread uint32_t __angora_context;

void __angora_reset_context() {
  __angora_prev_loc = 0;
  __angora_context = 0;
}
