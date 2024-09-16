#ifndef UNION_HASHTABLE_H
#define UNION_HASHTABLE_H

#include <stdint.h>
#include "sanitizer_common/sanitizer_internal_defs.h"
#include "taint_allocator.h"
#include "union_util.h"
#include "dfsan.h"

namespace __taint {

struct union_hashtable_entry {
  dfsan_label_info *key;
  dfsan_label entry;
  struct union_hashtable_entry *next;
};

class union_hashtable {
  struct union_hashtable_entry **bucket;
  uint64_t bucket_size;
  uint64_t hash(const dfsan_label_info &key);
  uint64_t hash_debug(const dfsan_label_info &key);
  uint64_t hash_debug1(const dfsan_label_info &key);
public:
  union_hashtable(uint64_t n);
  void insert(dfsan_label_info *key, dfsan_label value);
  option lookup(const dfsan_label_info &key);
};

}

#endif
