
#ifndef HEAPMAP_H
#define HEAPMAP_H

#ifdef __cplusplus
extern "C" {
#endif

void heapmap_set(void * base, size_t bound);
void heapmap_invalidate(void * base);
size_t heapmap_get(void * base);

#ifdef __cplusplus
}
#endif

#endif