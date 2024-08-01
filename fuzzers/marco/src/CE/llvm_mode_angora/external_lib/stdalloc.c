
// Memory functions
//
// The overrided functions will store the size of
// each function at the beginning of the allocated block.
// This allows for taint propagation during realloc() calls.

#include <assert.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/shm.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#include "./heapmap.h"
#include "./defs.h"
#include "./dfsan_interface.h"

__attribute__((visibility("default"))) void *
__dfsw_malloc(size_t size, dfsan_label size_label, dfsan_label *ret_label) {
  *ret_label = 0;
  DEBUG_PRINTF("============ In __dfsw_malloc() ============\n");
  DEBUG_PRINTF("Called with size = %lu\n", size);
  void *ptr = malloc(size);
  DEBUG_PRINTF("[+] malloc() returned %p\n", ptr);

  if (ptr) {
#ifdef ALLOC_PRELOAD
    DEBUG_PRINTF("[+] Base addresses recorded as %p, size recorded as %lu\n",
                 *((void **)(ptr - sizeof(void *) - sizeof(size_t))),
                 *((size_t *)(ptr - sizeof(size_t))));
#else
    heapmap_set(ptr, size);
#endif
  }
  fflush(stdout);
  return ptr;
}

__attribute__((visibility("default"))) void __dfsw_free(void *ptr,
                                                        dfsan_label ptr_label) {
  DEBUG_PRINTF("============ In __dfsw_free() ============\n");
  DEBUG_PRINTF("[+] free() called with pointer %p\n", ptr);
  free(ptr);
#ifndef ALLOC_PRELOAD
  heapmap_invalidate(ptr);
#endif
  fflush(stdout);
}

__attribute__((visibility("default"))) void *
__dfsw_calloc(size_t nmemb, size_t size, dfsan_label nmemb_label,
              dfsan_label size_label, dfsan_label *ret_label) {
  DEBUG_PRINTF("============ In __dfsw_calloc() ============\n");
  DEBUG_PRINTF("[+] calloc() called with nmemb = %lu, size = %lu\n", nmemb,
               size);
  *ret_label = 0;
  void *ptr = calloc(nmemb, size);
  DEBUG_PRINTF("[+] calloc() returned %p\n", ptr);
  if (ptr) {
#ifdef ALLOC_PRELOAD
    DEBUG_PRINTF("[+] Base addresses recorded as %p, size recorded as %lu\n",
                 *((void **)(ptr - sizeof(void *) - sizeof(size_t))),
                 *((size_t *)(ptr - sizeof(size_t))));
#else
    // Undefined behavior here.
    heapmap_set(ptr, nmemb * size);
#endif
  }
  fflush(stdout);
  return ptr;
}

__attribute__((visibility("default"))) void *
__dfsw_reallocarray(void *ptr, size_t nmemb, size_t size, dfsan_label ptr_label,
                    dfsan_label nmemb_label, dfsan_label size_label,
                    dfsan_label *ret_label) {
  // unimplemented
  abort();
  return NULL;
}

__attribute__((visibility("default"))) void *
__dfsw_realloc(void *ptr, size_t size, dfsan_label ptr_label,
               dfsan_label size_label, dfsan_label *ret_label) {
  DEBUG_PRINTF("============ In __dfsw_realloc() ============\n");
  DEBUG_PRINTF("[+] Called with ptr = %p, size = %lu\n", ptr, size);
  *ret_label = 0;
  // Retrieve metadata
#ifdef ALLOC_PRELOAD
  size_t old_size = *((size_t *)(ptr - sizeof(size_t)));
  void *old_base = *((void **)(ptr - sizeof(size_t) - sizeof(void *)));
  size_t prefix_size = ptr - old_base;
#else
  size_t old_size = heapmap_get(ptr);
  DEBUG_PRINTF("[+] Retrieved old size as %lu\n", old_size);
#endif

  //  DEBUG_PRINTF("[+] Old metadata retrieved as: base = %p, size = %lu\n",
  //  old_base, old_size);

  void *ret = realloc(ptr, size);

  DEBUG_PRINTF("[+] realloc() returned with %p\n", ret);

  if (ret) {
    if (ptr && ret != ptr) {
      DEBUG_PRINTF("[+] Base address changed. Copying labels to new area.\n");

#ifdef ALLOC_PRELOAD
      size_t new_size = *((size_t *)(ret - sizeof(size_t)));
      size_t new_base = *((void **)(ret - sizeof(size_t) - sizeof(void *)));
      DEBUG_PRINTF("[+] New metadata retrieved as: base = %p, size = %lu\n");
#else
      // size_t new_size = size;
      heapmap_invalidate(ptr);
#endif
      const dfsan_label *old_label_area = dfsan_shadow_for(ptr);
      dfsan_label *new_label_area = dfsan_shadow_for(ret);
      // DEBUG_PRINTF("[+] Before memcpy: old label = %u, new label = %u\n",
      //     dfsan_read_label(ptr, old_size),
      //     dfsan_read_label(ret, new_size));

      memcpy(new_label_area, old_label_area, sizeof(dfsan_label) * old_size);

      // DEBUG_PRINTF("[+] After memcpy: old label = %u, new label = %u\n",
      //     dfsan_read_label(ptr, old_size),
      //     dfsan_read_label(ret, new_size));
    }
#ifndef ALLOC_PRELOAD
    heapmap_set(ret, size);
#endif
  }
  fflush(stdout);
  return ret;
}
