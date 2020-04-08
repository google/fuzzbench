#include <stdlib.h>
#include <stdint.h>

// these are defined in the LLVM passes, 
// but need to be mocked for persistent mode.
uint32_t __afl_get_area_size(void) { abort(); }
uint32_t __afl_get_bbarea_size(void) { abort(); }