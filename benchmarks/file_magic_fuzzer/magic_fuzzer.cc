// Copyright 2016 Google Inc.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include <fcntl.h>
#include <libgen.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#include <magic.h>

#define likely(x)       __builtin_expect(!!(x), 1)
#define unlikely(x)     __builtin_expect(!!(x), 0)

struct Environment {
  Environment(std::string data_dir) {
    magic = magic_open(MAGIC_NONE);
    std::string magic_path = data_dir + "/magic";
    if (magic_load(magic, magic_path.c_str())) {
      fprintf(stderr, "error loading magic file: %s\n", magic_error(magic));
      exit(1);
    }
  }

  magic_t magic;
};

static Environment* env;
static char tmp_filename[32];
static int fd;


extern "C" int LLVMFuzzerInitialize(int* argc, char*** argv) {
  char* exe_path = (*argv)[0];
  // dirname() can modify its argument.
  char* exe_path_copy = strdup(exe_path);
  char* dir = dirname(exe_path_copy);
  env = new Environment(dir);
  free(exe_path_copy);

  strncpy(tmp_filename, "/tmp/fuzz.file-XXXXXX", 31);
  fd = mkstemp(tmp_filename);
  if (fd < 0) {
      printf("failed mkstemp, errno=%d\n", errno);
      return -2;
  }
  return 0;
}

extern "C" int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size) {
  if (size < 1)
    return 0;

  lseek(fd, 0, SEEK_SET);

  if (unlikely(write (fd, data, size) != size)) {
      printf("failed write, errno=%d\n", errno);
      close(fd);
      return -3;
  }
  if (unlikely(ftruncate(fd, size))) {
     printf("failed truncate, errno=%d\n", errno);
     close(fd);
     return -3;
  }
  lseek(fd, 0, SEEK_SET);

  magic_file(env->magic, tmp_filename);
  return 0;
}
