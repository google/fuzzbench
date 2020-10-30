// Copyright 2020 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.  // You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <vorbis/vorbisfile.h>

struct vorbis_data {
  const uint8_t *current;
  const uint8_t *data;
  size_t size;
};

size_t read_func(void *ptr, size_t size1, size_t size2, void *datasource) {
  struct vorbis_data* vd = (struct vorbis_data *)(datasource);
  size_t len = size1 * size2;
  if (vd->current + len > vd->data + vd->size) {
      len = vd->data + vd->size - vd->current;
  }
  memcpy(ptr, vd->current, len);
  vd->current += len;
  return len;
}


int LLVMFuzzerTestOneInput(const uint8_t *Data, size_t Size) {
  ov_callbacks memory_callbacks = {0};
  memory_callbacks.read_func = read_func;
  struct vorbis_data data_st;
  data_st.size = Size;
  data_st.current = Data;
  data_st.data = Data;
  OggVorbis_File vf;
  int result = ov_open_callbacks(&data_st, &vf, NULL, 0, memory_callbacks);
  if (result < 0) {
    return 0;
  }
  int current_section = 0;
  int eof = 0;
  char buf[4096];
  int read_result;
  while (!eof) {
    read_result = ov_read(&vf, buf, sizeof(buf), 0, 2, 1, &current_section);
    if (read_result != OV_HOLE && read_result <= 0) {
      eof = 1;
    }
  }
  ov_clear(&vf);
  return 0;
}
