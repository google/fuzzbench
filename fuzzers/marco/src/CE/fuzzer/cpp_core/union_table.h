typedef uint32_t dfsan_label;

struct dfsan_label_info {
  dfsan_label l1;
  dfsan_label l2;
  uint64_t op1;
  uint64_t op2;
  uint16_t op;
  uint16_t size;
  uint8_t flags;
  uint32_t tree_size;
  uint32_t hash;
  uint32_t depth;
  void* expr;
  void* deps;
} __attribute__((aligned (8)));
