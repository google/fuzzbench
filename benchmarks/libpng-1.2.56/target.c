// Copyright 2020 Google LLC
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

#include <stddef.h>
#include <string.h>
#include <stdint.h>
#include <assert.h>

#define PNG_INTERNAL  // For PNG_FLAG_CRC_CRITICAL_MASK, etc.
#include "png.h"

struct BufState {
  const uint8_t* data;
  size_t bytes_left;
};

void user_read_data(png_structp png_ptr, png_bytep data, png_size_t length) {
  struct BufState* buf_state = (struct BufState*)(png_get_io_ptr(png_ptr));
  if (length > buf_state->bytes_left) {
    png_error(png_ptr, "read error");
  }
  memcpy(data, buf_state->data, length);
  buf_state->bytes_left -= length;
  buf_state->data += length;
}

static const int kPngHeaderSize = 8;

// Fuzzing entry point. Roughly follows the libpng book example:
// http://www.libpng.org/pub/png/book/chapter13.html
int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size) {
  if (size < kPngHeaderSize) {
    return 0;
  }

  if (png_sig_cmp((uint8_t*)data, 0, kPngHeaderSize)) {
    // not a PNG.
    return 0;
  }


  png_structp png_ptr = png_create_read_struct
    (PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);
  assert(png_ptr);

  (png_ptr)->flags &= ~PNG_FLAG_CRC_CRITICAL_MASK;
  (png_ptr)->flags |= PNG_FLAG_CRC_CRITICAL_IGNORE;

  (png_ptr)->flags &= ~PNG_FLAG_CRC_ANCILLARY_MASK;
  (png_ptr)->flags |= PNG_FLAG_CRC_ANCILLARY_NOWARN;

  png_infop  info_ptr = png_create_info_struct(png_ptr);
  assert(info_ptr);

  // Setting up reading from buffer.
  struct BufState* buf_state = (struct BufState*)malloc(sizeof(struct BufState));
  (buf_state)->data = data + kPngHeaderSize;
  (buf_state)->bytes_left = size - kPngHeaderSize;
  png_set_read_fn(png_ptr, buf_state, user_read_data);
  png_set_sig_bytes(png_ptr, kPngHeaderSize);
  int passes = 0;

  // libpng error handling.
  if (setjmp((png_ptr)->jmpbuf)) {
    return 0;
  }

  // Reading
  png_read_info(png_ptr, info_ptr);

  png_uint_32 width, height;
  int bit_depth, color_type, interlace_type, compression_type;
  int filter_type;

  if (!png_get_IHDR(png_ptr, info_ptr, &width, &height,
        &bit_depth, &color_type, &interlace_type,
        &compression_type, &filter_type)) {
    return 0;
  }

  if (height * width > 2000000) return 0;  // This is going to be too slow.


  passes = png_set_interlace_handling(png_ptr);
  png_start_read_image(png_ptr);

  png_voidp row = png_malloc(png_ptr, png_get_rowbytes(png_ptr, info_ptr));

  for (int pass = 0; pass < passes; ++pass) {
    for (png_uint_32 y = 0; y < height; ++y) {
      png_read_row(png_ptr, (png_bytep)(row), NULL);
    }
  }
	if (row && png_ptr) {
      png_free(png_ptr, row);
  }
  if (png_ptr && info_ptr) {
      png_destroy_read_struct(&png_ptr, &info_ptr, NULL);
  }
  free (buf_state);

  return 0;
}
