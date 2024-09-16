#include "../sanitizer_common/sanitizer_libc.h"
#include "union_hashtable.h"
#include "union_util.h"

using namespace __taint;

union_hashtable::union_hashtable(uint64_t n) {
  bucket_size = n;
  bucket = (struct union_hashtable_entry **)
    allocator_alloc(n * sizeof(struct union_hashtable_entry *));
  __sanitizer::internal_memset(bucket, 0, n * sizeof(struct union_hashtable_entry *));
}

uint64_t
union_hashtable::hash(const dfsan_label_info &key) {
  return ((key.l1 + key.l2 + key.op1 + key.op2) ^ (key.op << 3) ^ key.size) 
      & (bucket_size - 1);
}

void
union_hashtable::insert(dfsan_label_info *key, dfsan_label entry) {
  uint64_t index = hash(*key);
  auto curr = (struct union_hashtable_entry *)
      allocator_alloc(sizeof(struct union_hashtable_entry));
  curr->key = key; curr->entry = entry;
  curr->next = bucket[index];
  bucket[index] = curr;
}

option
union_hashtable::lookup(const dfsan_label_info &key) {
  uint64_t index = hash(key);
  auto curr = bucket[index];
  while (curr) {
    if (*(curr->key) == key) {
      return some_dfsan_label(curr->entry);
    }
    curr = curr->next;
  }
  return none();
}
