#ifndef _INPUT_H_
#define _INPUT_H_
#include <stddef.h>
#include <stdint.h>
#include <vector>
#include <string.h>
#include <stdlib.h>
#include <utility>

class InputMeta {
public:
  bool sign;
  size_t offset;
  size_t size;
};


class MutInput {
public:
 // std::vector<uint8_t> value;
	uint8_t* value;
	uint8_t* disables;
 // std::vector<InputMeta> meta;
	size_t size_;
	size_t get_size();
  MutInput(size_t size);
	~MutInput();	
	void dump();
  uint64_t len();
  uint64_t val_len();
  void randomize();
	//random
	char r_s[256];
  struct random_data r_d;
	int32_t r_val;
	int32_t r_idx;
	uint8_t get_rand();

  void resetDisables();
  void setDisable(size_t i);
  uint8_t get(size_t i);
  void update(size_t index, bool direction, uint64_t delta);
  void flip(size_t index, size_t bit_index);
  void set(size_t index, uint8_t value);
	void assign(std::vector<std::pair<uint32_t,uint8_t>> &input);
	MutInput& operator=(const MutInput &other);
	
	static void copy(MutInput *dst, const MutInput *src)
  {
      uint8_t *dst_value = dst->value;
      memcpy(dst, src, sizeof(MutInput));
      if (!dst_value)
        dst->value = (uint8_t*)malloc(src->size_);
      else
        dst->value = dst_value;
      memcpy(dst->value, src->value, src->size_);
  }
};
#endif
