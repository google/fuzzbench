/*
  C IO Proxy Function

  to write custom functions, modify custom/angora_abilist.txt first
 */

#include <assert.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#include "./ffds.h"
#include "./len_label.h"
#include "./defs.h"
#include "./dfsan_interface.h"

static int granularity = 1; // byte level

extern void __angora_track_fini_rs();

__attribute__((destructor(0))) void __angora_track_fini(void) {
  __angora_track_fini_rs();
}

#define __angora_get_sp_label __angora_get_len_label
#define is_fuzzing_fd __angora_io_find_fd
#define is_fuzzing_ffd __angora_io_find_pfile
#define add_fuzzing_fd __angora_io_add_fd
#define add_fuzzing_ffd __angora_io_add_pfile
#define remove_fuzzing_fd __angora_io_remove_fd
#define remove_fuzzing_ffd __angora_io_remove_pfile

static void assign_taint_labels(void *buf, long offset, size_t size) {
  for (size_t i = 0; i < size; i += granularity) {
    // start from 0
    dfsan_label L = dfsan_create_label(offset + i);
    if (size < i + granularity)
      dfsan_set_label(L, (char *)(buf) + i, size - i);
    else
      dfsan_set_label(L, (char *)(buf) + i, granularity);
  }
}

static void assign_taint_labels_exf(void *buf, long offset, size_t ret,
                                    size_t count, size_t size) {
  if (offset < 0)
    offset = 0;
  // if count is not so huge!
  int len = ret * size;
  if (ret < count) {
    int res = (count - ret) * size;
    if (res < 1024) {
      len += res;
    } else {
      len += 1024;
    }
  }
  assign_taint_labels(buf, offset, len);
}

#define IS_FUZZING_FILE(filename) strstr(filename, FUZZING_INPUT_FILE)

__attribute__((visibility("default"))) int
__dfsw_open(const char *path, int oflags, dfsan_label path_label,
            dfsan_label flag_label, dfsan_label *va_labels,
            dfsan_label *ret_label, ...) {

  va_list args;
  va_start(args, ret_label);
  int fd = open(path, oflags, args);
  va_end(args);

#ifdef DEBUG_INFO
  fprintf(stderr, "### open, filename is : %s, fd is %d \n", path, fd);
#endif

  if (fd >= 0 && IS_FUZZING_FILE(path)) {
    add_fuzzing_fd(fd);
  }

  *ret_label = 0;
  return fd;
}

__attribute__((visibility("default"))) FILE *
__dfsw_fopen(const char *filename, const char *mode, dfsan_label fn_label,
             dfsan_label mode_label, dfsan_label *ret_label) {

  FILE *fd = fopen(filename, mode);

#ifdef DEBUG_INFO
  fprintf(stderr, "### fopen, filename is : %s, fd is %p \n", filename, fd);
#endif

  if (fd && IS_FUZZING_FILE(filename)) {
    add_fuzzing_ffd(fd);
  }

  *ret_label = 0;
  return fd;
}
__attribute__((visibility("default"))) FILE *
__dfsw_fopen64(const char *filename, const char *mode, dfsan_label fn_label,
               dfsan_label mode_label, dfsan_label *ret_label) {
  FILE *fd = fopen(filename, mode);

#ifdef DEBUG_INFO
  fprintf(stderr, "### fopen64, filename is : %s, fd is %p \n", filename, fd);
  fflush(stderr);
#endif

  if (fd && IS_FUZZING_FILE(filename)) {
    add_fuzzing_ffd(fd);
  }

  *ret_label = 0;
  return fd;
}

__attribute__((visibility("default"))) int
__dfsw_close(int fd, dfsan_label fd_label, dfsan_label *ret_label) {

  int ret = close(fd);
#ifdef DEBUG_INFO
  fprintf(stderr, "### close, fd is %d , ret is %d \n", fd, ret);
#endif

  if (ret == 0 && is_fuzzing_fd(fd)) {
    remove_fuzzing_fd(fd);
  }

  *ret_label = 0;
  return ret;
}

__attribute__((visibility("default"))) int
__dfsw_fclose(FILE *fd, dfsan_label fd_label, dfsan_label *ret_label) {

  int ret = fclose(fd);
#ifdef DEBUG_INFO
  fprintf(stderr, "### close, fd is %p, ret is %d \n", fd, ret);
#endif
  if (ret == 0 && is_fuzzing_ffd(fd)) {
    remove_fuzzing_ffd(fd);
  }
  *ret_label = 0;
  return ret;
}

__attribute__((visibility("default"))) void *
__dfsw_mmap(void *start, size_t length, int prot, int flags, int fd,
            off_t offset, dfsan_label start_label, dfsan_label len_label,
            dfsan_label prot_label, dfsan_label flags_label,
            dfsan_label fd_label, dfsan_label offset_label,
            dfsan_label *ret_label) {
#ifdef DEBUG_INFO
  fprintf(stderr, "### mmap, fd is %d, addr %x, offset: %ld, length %d \n", fd,
          offset, length);
#endif
  void *ret = mmap(start, length, prot, flags, fd, offset);
  if (ret > 0 && is_fuzzing_fd(fd)) {
    assign_taint_labels(ret, offset, length);
  }
  *ret_label = 0;
  return ret;
}

// void *mmap2(void *addr, size_t length, int prot, int flags, int fd, off_t
// pgoffset); pgoffset: offset of page = *4096 bytes

__attribute__((visibility("default"))) int
__dfsw_munmap(void *addr, size_t length, dfsan_label addr_label,
              dfsan_label length_label, dfsan_label *ret_label) {
  // clear sth
#ifdef DEBUG_INFO
  fprintf(stderr, "### munmap, addr %x, length %d \n", addr, length);
#endif
  int ret = munmap(addr, length);
  dfsan_set_label(0, addr, length);
  *ret_label = 0;
  return ret;
}

__attribute__((visibility("default"))) size_t
__dfsw_fread(void *buf, size_t size, size_t count, FILE *fd,
             dfsan_label buf_label, dfsan_label size_label,
             dfsan_label count_label, dfsan_label fd_label,
             dfsan_label *ret_label) {
  long offset = ftell(fd);
  size_t ret = fread(buf, size, count, fd);
#ifdef DEBUG_INFO
  fprintf(stderr, "### fread %p,range is %ld, %ld  --  (size %d, count %d)\n",
          fd, offset, ret, size, count);
#endif
  if (is_fuzzing_ffd(fd)) {
    if (ret > 0)
      assign_taint_labels_exf(buf, offset, ret, count, size);
    *ret_label = __angora_get_sp_label(offset, size);
  } else {
    *ret_label = 0;
  }
  return ret;
}

__attribute__((visibility("default"))) size_t
__dfsw_fread_unlocked(void *buf, size_t size, size_t count, FILE *fd,
                      dfsan_label buf_label, dfsan_label size_label,
                      dfsan_label count_label, dfsan_label fd_label,
                      dfsan_label *ret_label) {
  long offset = ftell(fd);
  size_t ret = fread_unlocked(buf, size, count, fd);
#ifdef DEBUG_INFO
  fprintf(stderr, "### fread_unlocked %p,range is %ld, %ld/%ld\n", fd, offset,
          ret, count);
#endif
  if (is_fuzzing_ffd(fd)) {
    if (ret > 0)
      assign_taint_labels_exf(buf, offset, ret, count, size);
    *ret_label = __angora_get_sp_label(offset, size);
  } else {
    *ret_label = 0;
  }
  return ret;
}

__attribute__((visibility("default"))) ssize_t
__dfsw_read(int fd, void *buf, size_t count, dfsan_label fd_label,
            dfsan_label buf_label, dfsan_label count_label,
            dfsan_label *ret_label) {

  long offset = lseek(fd, 0, SEEK_CUR);
  ssize_t ret = read(fd, buf, count);
#ifdef DEBUG_INFO
  fprintf(stderr, "### read %d, range is %ld, %ld/%ld \n", fd, offset, ret,
          count);
#endif
  if (is_fuzzing_fd(fd)) {
    if (ret > 0)
      assign_taint_labels_exf(buf, offset, ret, count, 1);
    *ret_label = __angora_get_sp_label(offset, 1);
  } else {
    *ret_label = 0;
  }
  return ret;
}

__attribute__((visibility("default"))) ssize_t
__dfsw_pread(int fd, void *buf, size_t count, off_t offset,
             dfsan_label fd_label, dfsan_label buf_label,
             dfsan_label count_label, dfsan_label offset_label,
             dfsan_label *ret_label) {
  ssize_t ret = pread(fd, buf, count, offset);
#ifdef DEBUG_INFO
  fprintf(stderr, "### pread %d, range is %ld, %ld/%ld \n", fd, offset, ret,
          count);
#endif
  if (is_fuzzing_fd(fd)) {
    if (ret > 0)
      assign_taint_labels_exf(buf, offset, ret, count, 1);
    *ret_label = __angora_get_sp_label(offset, 1);
  } else {
    *ret_label = 0;
  }
  return ret;
}

__attribute__((visibility("default"))) int
__dfsw_fgetc(FILE *fd, dfsan_label fd_label, dfsan_label *ret_label) {

  long offset = ftell(fd);
  int c = fgetc(fd);
  *ret_label = 0;
#ifdef DEBUG_INFO
  fprintf(stderr, "### fgetc %p, range is %ld, 1 \n", fd, offset);
#endif
  if (c != EOF && is_fuzzing_ffd(fd)) {
    dfsan_label l = dfsan_create_label(offset);
    *ret_label = l;
  }
  return c;
}
__attribute__((visibility("default"))) int
__dfsw_fgetc_unlocked(FILE *fd, dfsan_label fd_label, dfsan_label *ret_label) {

  long offset = ftell(fd);
  int c = fgetc_unlocked(fd);
  *ret_label = 0;
#ifdef DEBUG_INFO
  fprintf(stderr, "### fgetc_unlocked %p, range is %ld, 1 \n", fd, offset);
#endif
  if (c != EOF && is_fuzzing_ffd(fd)) {
    dfsan_label l = dfsan_create_label(offset);
    *ret_label = l;
  }
  return c;
}

__attribute__((visibility("default"))) int
__dfsw__IO_getc(FILE *fd, dfsan_label fd_label, dfsan_label *ret_label) {
  long offset = ftell(fd);
  int c = getc(fd);
  *ret_label = 0;
#ifdef DEBUG_INFO
  fprintf(stderr, "### _IO_getc %p, range is %ld, 1 , c is %d\n", fd, offset,
          c);
#endif
  if (is_fuzzing_ffd(fd) && c != EOF) {
    dfsan_label l = dfsan_create_label(offset);
    *ret_label = l;
  }
  return c;
}

__attribute__((visibility("default"))) int
__dfsw_getchar(dfsan_label *ret_label) {

  long offset = ftell(stdin);
  int c = getchar();
  *ret_label = 0;
#ifdef DEBUG_INFO
  fprintf(stderr, "### getchar stdin, range is %ld, 1 \n", offset);
#endif
  if (c != EOF) {
    dfsan_label l = dfsan_create_label(offset);
    *ret_label = l;
  }
  return c;
}

__attribute__((visibility("default"))) char *
__dfsw_fgets(char *str, int count, FILE *fd, dfsan_label str_label,
             dfsan_label count_label, dfsan_label fd_label,
             dfsan_label *ret_label) {

  long offset = ftell(fd);
  char *ret = fgets(str, count, fd);
#ifdef DEBUG_INFO
  fprintf(stderr, "fgets %p, range is %ld, %ld \n", fd, offset, strlen(ret));
#endif
  if (ret && is_fuzzing_ffd(fd)) {
    int len = strlen(ret); // + 1?
    assign_taint_labels_exf(str, offset, len, count, 1);
    *ret_label = str_label;
  } else {
    *ret_label = 0;
  }
  return ret;
}

/*
__attribute__((visibility("default"))) char *
__dfsw_fgets_unlocked(char *str, int count, FILE *fd, dfsan_label str_label,
                      dfsan_label count_label, dfsan_label fd_label,
                      dfsan_label *ret_label) {

  long offset = ftell(fd);
  char *ret = fgets_unlocked(str, count, fd);
#ifdef DEBUG_INFO
  fprintf(stderr, "fgets_unlocked %p, range is %ld, %ld \n", fd, offset,
          strlen(ret) + 1);
#endif
  if (ret && is_fuzzing_ffd(fd)) {
    assign_taint_labels(str, offset, strlen(ret) + 1);
    *ret_label = str_label;
  } else {
    *ret_label = 0;
  }
  return ret;
}
*/

__attribute__((visibility("default"))) char *
__dfsw_gets(char *str, dfsan_label str_label, dfsan_label *ret_label) {
  long offset = ftell(stdin);
  // gets discard until c11
  char *ret = fgets(str, sizeof str, stdin);
#ifdef DEBUG_INFO
  fprintf(stderr, "gets stdin, range is %ld, %ld \n", offset, strlen(ret) + 1);
#endif
  if (ret) {
    assign_taint_labels(str, offset, strlen(ret) + 1);
    *ret_label = str_label;
  } else {
    *ret_label = 0;
  }
  return ret;
}

#include <utmp.h>
// int utmpname(const char *file);
// https://linux.die.net/man/3/utmpxname
// should maintain
// FIXME: only work in binutils/who?
// If current name == who?
static size_t __rt_utmp_offset = 0;
__attribute__((visibility("default"))) struct utmp *
__dfsw_getutxent(dfsan_label *ret_label) {

  struct utmp *ret = getutent();
  size_t len = sizeof(struct utmp);
#ifdef DEBUG_INFO
  fprintf(stderr, "getutxent, range is %ld, %ld \n", __rt_utmp_offset, len);
#endif
  if (ret) {
    assign_taint_labels(ret, __rt_utmp_offset, len);
    __rt_utmp_offset += len;
  }

  *ret_label = 0;
  return ret;
}

// ssize_t getline(char **lineptr, size_t *n, FILE *stream);
__attribute__((visibility("default"))) ssize_t
__dfsw_getline(char **lineptr, size_t *n, FILE *fd, dfsan_label buf_label,
               dfsan_label size_label, dfsan_label fd_label,
               dfsan_label *ret_label) {
  long offset = ftell(fd);
  ssize_t ret = getline(lineptr, n, fd);
#ifdef DEBUG_INFO
  fprintf(stderr, "### getline %p,range is %ld, %ld\n", fd, offset, ret);
#endif
  if (is_fuzzing_ffd(fd)) {
    if (ret > 0)
      assign_taint_labels(*lineptr, offset, ret);
    *ret_label = __angora_get_sp_label(offset, 1);
  } else {
    *ret_label = 0;
  }
  return ret;
}

// ssize_t getdelim(char **lineptr, size_t *n, int delim, FILE *stream);
__attribute__((visibility("default"))) ssize_t
__dfsw_getdelim(char **lineptr, size_t *n, int delim, FILE *fd,
                dfsan_label buf_label, dfsan_label size_label,
                dfsan_label delim_label, dfsan_label fd_label,
                dfsan_label *ret_label) {
  long offset = ftell(fd);
  ssize_t ret = getdelim(lineptr, n, delim, fd);
#ifdef DEBUG_INFO
  fprintf(stderr, "### getdelim %p,range is %ld, %ld\n", fd, offset, ret);
#endif
  if (ret > 0 && is_fuzzing_ffd(fd)) {
    assign_taint_labels(*lineptr, offset, ret);
  }
  *ret_label = 0;
  return ret;
}

__attribute__((visibility("default"))) ssize_t
__dfsw___getdelim(char **lineptr, size_t *n, int delim, FILE *fd,
                  dfsan_label buf_label, dfsan_label size_label,
                  dfsan_label delim_label, dfsan_label fd_label,
                  dfsan_label *ret_label) {
  long offset = ftell(fd);
  ssize_t ret = __getdelim(lineptr, n, delim, fd);
#ifdef DEBUG_INFO
  fprintf(stderr, "### __getdelim %p,range is %ld, %ld\n", fd, offset, ret);
#endif
  if (ret > 0 && is_fuzzing_ffd(fd)) {
    assign_taint_labels(*lineptr, offset, ret);
  }
  *ret_label = 0;
  return ret;
}

// strcat

// fscanf

// int stat(const char *path, struct stat *buf);
__attribute__((visibility("default"))) int
__dfsw_stat(const char *path, struct stat *buf, dfsan_label path_label,
            dfsan_label buf_label, dfsan_label *ret_label) {

  int ret = stat(path, buf);

  // fprintf(stderr, "run stat .. %d\n", ret);
  if (ret >= 0) {
    dfsan_set_label(0, buf, sizeof(struct stat));
    dfsan_label lb = __angora_get_sp_label(0, 1);
    dfsan_set_label(lb, (char *)&(buf->st_size), sizeof(buf->st_size));
  }
  *ret_label = 0;
  return ret;
}

__attribute__((visibility("default"))) int
__dfsw___xstat(int vers, const char *path, struct stat *buf,
               dfsan_label vers_label, dfsan_label path_label,
               dfsan_label buf_label, dfsan_label *ret_label) {

  int ret = __xstat(vers, path, buf);

  // fprintf(stderr, "run stat .. %d\n", ret);
  if (ret >= 0) {
    dfsan_set_label(0, buf, sizeof(struct stat));
    dfsan_label lb = __angora_get_sp_label(0, 1);
    dfsan_set_label(lb, (char *)&(buf->st_size), sizeof(buf->st_size));
  }
  *ret_label = 0;
  return ret;
}

// int fstat(int fd, struct stat *buf);
__attribute__((visibility("default"))) int
__dfsw_fstat(int fd, struct stat *buf, dfsan_label fd_label,
             dfsan_label buf_label, dfsan_label *ret_label) {

  int ret = fstat(fd, buf);

  if (ret >= 0) {
    dfsan_set_label(0, buf, sizeof(struct stat));
    dfsan_label lb = __angora_get_sp_label(0, 1);
    dfsan_set_label(lb, (char *)&(buf->st_size), sizeof(buf->st_size));
  }

  *ret_label = 0;
  return ret;
}

__attribute__((visibility("default"))) int
__dfsw___fxstat(int vers, const int fd, struct stat *buf,
                dfsan_label vers_label, dfsan_label fd_label,
                dfsan_label buf_label, dfsan_label *ret_label) {

  int ret = __fxstat(vers, fd, buf);

  // fprintf(stderr, "run stat .. %d\n", ret);
  if (ret >= 0) {
    dfsan_set_label(0, buf, sizeof(struct stat));
    dfsan_label lb = __angora_get_sp_label(0, 1);
    dfsan_set_label(lb, (char *)&(buf->st_size), sizeof(buf->st_size));
  }
  *ret_label = 0;
  return ret;
}

// int lstat(const char *path, struct stat *buf);
__attribute__((visibility("default"))) int
__dfsw_lstat(const char *path, struct stat *buf, dfsan_label path_label,
             dfsan_label buf_label, dfsan_label *ret_label) {

  int ret = lstat(path, buf);

  if (ret >= 0) {
    dfsan_set_label(0, buf, sizeof(struct stat));
    dfsan_label lb = __angora_get_sp_label(0, 1);
    dfsan_set_label(lb, (char *)&(buf->st_size), sizeof(buf->st_size));
  }

  *ret_label = 0;
  return ret;
}

__attribute__((visibility("default"))) int
__dfsw___lxstat(int vers, const char *path, struct stat *buf,
                dfsan_label vers_label, dfsan_label path_label,
                dfsan_label buf_label, dfsan_label *ret_label) {

  int ret = __lxstat(vers, path, buf);

  //  fprintf(stderr, "run stat .. %d\n", ret);
  if (ret >= 0) {
    dfsan_set_label(0, buf, sizeof(struct stat));
    dfsan_label lb = __angora_get_sp_label(0, 1);
    dfsan_set_label(lb, (char *)&(buf->st_size), sizeof(buf->st_size));
  }
  *ret_label = 0;
  return ret;
}
