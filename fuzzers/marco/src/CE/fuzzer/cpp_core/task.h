#ifndef TEST_H_
#define TEST_H_
#include <stdint.h>
#include <vector>
#include <map>
#include <memory>
#include <unordered_map>
#include "grad.h"
#include "input.h"
//function under test
//constraint: 0 = equal, 1 = distinct, 2 = lt, 3 = le, 4 = gt, 5 = ge 
typedef uint64_t(*test_fn_type)(uint64_t*);

class SContext {
public:
  //the input when the searching task exit
  MutInput scratch_input;
  MutInput min_input;
  Grad grad;
  //use distances to represent distance for each sub-expr
  std::vector<uint64_t> distances;
  std::vector<uint64_t> orig_distances;
  //0: load_input 1: gradient 2: guess descend 3: all dimension descend 4, one dimension descend 5: randomize
  int next_state;
  int step;
  uint64_t f_last; //the last distance
  int dimensionIdx;
  int att;
  bool solved;
  SContext(size_t len, size_t num_exprs):
      orig_distances(num_exprs,0),
      distances(num_exprs,0),
      scratch_input(len),
      min_input(len),
      grad(len),
      step(1),
      f_last(-1),
      dimensionIdx(0),
      att(0),
      solved(false),
      next_state(0) {}
};

class Cons {
public:
	test_fn_type fn;
	uint32_t comparison;

	//map the offset to the idx in inputs_args
	std::unordered_map<uint32_t,uint32_t> local_map;
	// if const {false, const value}, if symbolic {true, index in the inputs}
	std::vector<std::pair<bool, uint64_t>> input_args;
	//map the offset to iv
	std::unordered_map<uint32_t,uint8_t> inputs;
	uint32_t const_num;
};

struct FUT {  
	FUT(): scratch_args(nullptr), max_const_num(0) {}
	~FUT() { if (scratch_args) free(scratch_args); if (ctx) delete ctx;}
	uint32_t num_exprs;
	std::vector<std::shared_ptr<Cons>> constraints;

	// offset and input value
	std::vector<std::pair<uint32_t,uint8_t>> inputs;

  //Context
  SContext *ctx;
	uint64_t start; //start time
	uint32_t max_const_num;
	bool opti_hit = false;
  std::vector<std::unordered_map<uint32_t,uint8_t>> *rgd_solutions;
  std::vector<std::unordered_map<uint32_t,uint8_t>> *partial_solutions;
	std::unordered_map<uint32_t,uint8_t> *rgd_solution;
	std::unordered_map<uint32_t,uint8_t> *opti_solution;
	uint64_t* scratch_args;
	//void allocate_scratch_args(int size) {scratch_args = (uint8_t*)aligned_alloc(64,size);}
	void finalize() {
	  //aggregate the contraints, fill input_args's index, build global inputs
		std::unordered_map<uint32_t,uint32_t> sym_map;
		uint32_t gidx = 0;
		for (size_t i =0; i< constraints.size(); i++) {
			for (auto itr : constraints[i]->local_map) {
				auto gitr = sym_map.find(itr.first);
				if (gitr == sym_map.end()) {
					gidx = inputs.size();
					sym_map[itr.first] = gidx;
					inputs.push_back(std::make_pair(itr.first,constraints[i]->inputs[itr.first]));
				} else {
					gidx = gitr->second;
				}
				constraints[i]->input_args[itr.second].second = gidx;  //update input_args
			}
		}

		for (size_t i=0; i < constraints.size(); i++) {
			if (max_const_num < constraints[i]->const_num)
				max_const_num = constraints[i]->const_num;
		}

		scratch_args = (uint64_t*)malloc((2 + inputs.size() + max_const_num) * sizeof(uint64_t));
    ctx = new SContext(inputs.size(), constraints.size());
	}

  void load_hint(std::unordered_map<uint32_t,uint8_t> &hint_solution) {// load hint
    for(auto itr = inputs.begin(); itr!=inputs.end();itr++) {
      auto got = hint_solution.find(itr->first);
      if (got != hint_solution.end())
        itr->second = got->second;
    }
  }

};
#endif
