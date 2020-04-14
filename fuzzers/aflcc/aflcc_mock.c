#include <stdlib.h>
#include <stdint.h>

// these are defined in the LLVM passes, 
// but need to be mocked for persistent mode.
void __afl_manual_init(void) { printf("manual_init\n"); }
int __afl_persistent_loop(unsigned int max_cnt) { printf("peristent loop\n"); return 0; }
uint32_t __afl_get_area_size(void) { printf("get area size\n"); return 0; }
uint32_t __afl_get_bbarea_size(void) { printf("bb area size\n"); return 0; }