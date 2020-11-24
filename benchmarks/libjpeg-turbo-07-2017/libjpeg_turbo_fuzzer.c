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

#include <stdint.h>
#include <stdlib.h>

#include <memory.h>

#include <turbojpeg.h>

#ifdef KIRENENKO
int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
#else
extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
#endif
    tjhandle jpegDecompressor = tjInitDecompress();

    int width, height, subsamp, colorspace;
    int res = tjDecompressHeader3(
        jpegDecompressor, data, size, &width, &height, &subsamp, &colorspace);

    // Bail out if decompressing the headers failed, the width or height is 0,
    // or the image is too large (avoids slowing down too much). Cast to size_t to
    // avoid overflows on the multiplication
    if (res != 0 || width == 0 || height == 0 || ((size_t)width * height > (1024 * 1024))) {
        tjDestroy(jpegDecompressor);
        return 0;
    }

	unsigned char* buf = (unsigned char *)malloc(width*height*3);
    tjDecompress2(
        jpegDecompressor, data, size, buf, width, 0, height, TJPF_RGB, 0);

    tjDestroy(jpegDecompressor);
    free(buf);

    return 0;
}
