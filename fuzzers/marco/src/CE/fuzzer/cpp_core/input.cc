#include "input.h"
#include <ctime>
#include <cstdlib>
#include <iostream>
#include <cstring>

void MutInput::update(size_t index, bool direction, uint64_t delta)
{
  if (disables[index]==0) {
	if (direction)
		value[index] += delta;
	else
		value[index] -= delta;
  }
}

uint8_t MutInput::get_rand()
{
  uint8_t r = (uint8_t)r_val;
  r_val >>= 8;
  r_idx++;
  if (r_idx == 4) {
    random_r(&r_d, &r_val);
    r_idx = 0;
  }
  return r;
}


void MutInput::assign(std::vector<std::pair<uint32_t,uint8_t>> &input) {
	for(int i=0;i<size_;i++) {
		value[i] =  input[i].second;
		//std::cout << "randomize " << i << " and assign value " << (int)value[i] << std::endl;
	}
}

void MutInput::flip(size_t index, size_t bit_index) {
	uint8_t val = value[index];
	uint8_t mask = 1;
	mask = mask << bit_index;
	value[index] = val^mask;
}

void MutInput::set(size_t index, uint8_t val)
{
	value[index] = val;
}

uint64_t MutInput::len() {
	return size_;
}


uint64_t MutInput::val_len() {
	return size_;
}

MutInput& MutInput::operator =(const MutInput &other)
{
  MutInput::copy(this, &other);
  return *this;
}

void MutInput::dump() {
//	printf("dumping input and value size is %lu\n",value.size());
	//for(auto i : value)
//		printf("%d, ",i);
//	printf("\n");
}

void MutInput::randomize() {
	for(int i=0;i<size_;i++) {
    if (disables[i]==0)
		  value[i] = get_rand();
		//std::cout << "randomize " << i << " and assign value " << (int)value[i] << std::endl;
	}
}

uint8_t MutInput::get(size_t i) {
	return value[i];
}

MutInput::MutInput(size_t size)  {
  r_idx = 0;
	value = (uint8_t*)malloc(size);
  disables = (uint8_t*)malloc(size);
  memset(disables, 0, size);
	size_ = size;
	unsigned int seed;
  //_rdseed32_step(&seed);
	seed = (unsigned)time(NULL);
  memset(r_s, 0, 256);
  memset(&r_d, 0, sizeof(struct random_data));
  initstate_r(seed, r_s, 256, &r_d);
  random_r(&r_d, &r_val);
}

void MutInput::resetDisables() {
  memset(disables, 0, size_);
}

void MutInput::setDisable(size_t idx) {
  disables[idx] = 1;
}

MutInput::~MutInput()
{
  if (value)
    free(value);
  if (disables)
    free(disables);
}
