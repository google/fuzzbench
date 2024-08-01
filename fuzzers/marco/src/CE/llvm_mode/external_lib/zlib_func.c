#include <zlib.h>
#include "./defs.h"
#include "./dfsan_interface.h"

// zlib_abilist line 104: fn:crc32=custom
__attribute__((visibility("default"))) uLong
__dfsw_crc32(uLong crc, const Bytef * buf, uInt len,
             dfsan_label crc_label, dfsan_label buf_label, dfsan_label len_label,
             dfsan_label *ret_label) {

  crc_label = dfsan_union(crc_label, len_label);
  crc_label = dfsan_union(crc_label, dfsan_read_label(buf, len * sizeof(Bytef)));
  crc = crc32(crc, buf, len);
  *ret_label = crc_label;

  return crc;

}
