#ifndef ANGORA_TAG_SET_H
#define ANGORA_TAG_SET_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

uint32_t __angora_tag_set_insert(uint32_t offset);

uint32_t __angora_tag_set_combine(uint32_t lb1, uint32_t lb2);

uint32_t __angora_tag_set_combine_n(const uint32_t *lbs, uint32_t size,
                                    bool infer_shape);

void __angora_tag_set_mark_sign(uint32_t lb);

void __angora_tag_set_infer_shape_in_math_op(uint32_t lb, uint32_t len);

void __angora_tag_set_combine_and(uint32_t lb);

void __angora_tag_set_fini();

#ifdef __cplusplus
}
#endif

#endif
