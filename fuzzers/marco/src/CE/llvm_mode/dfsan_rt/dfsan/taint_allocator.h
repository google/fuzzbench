#ifndef UNION_ALLOCATOR_H
#define UNION_ALLOCATOR_H

#include "sanitizer_common/sanitizer_internal_defs.h"

using __sanitizer::uptr;

namespace __taint {

void allocator_init(uptr begin, uptr end);
void *allocator_alloc(uptr size);
void allocator_dealloc(uptr addr);

} // namespace

#endif // UNION_ALLOCATOR_H
