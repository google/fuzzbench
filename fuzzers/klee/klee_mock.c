// mock for a KLEE internal function
// We build it as a shared library for gclang
#include <stdlib.h>
void klee_make_symbolic(void *addr, size_t len, char const* name) {
	// do nothing
	abort();
}