#ifndef FFDS_H
#define FFDS_H
#include <stdint.h>
#include <stdio.h>
typedef uint32_t u32;
#ifdef __cplusplus
extern "C" {
#endif

u32 __angora_io_find_fd(int fd);
u32 __angora_io_find_pfile(FILE *f);
void __angora_io_add_fd(int fd);
void __angora_io_add_pfile(FILE *f);
void __angora_io_remove_fd(int fd);
void __angora_io_remove_pfile(FILE *f);

#ifdef __cplusplus
}

#endif

#endif
