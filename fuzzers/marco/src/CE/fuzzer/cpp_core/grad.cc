#include "grad.h"
#include <stdint.h>
#include <iostream>

Grad::Grad(size_t size) : grads(size) {
}

std::vector<GradUnit>& Grad::get_value() {
	return grads;
}

void Grad::print() {
  for(auto item : grads) {
    printf("sign is %u, val is %lu, pct is %f\n", item.sign, item.val, item.pct);
  }
}


uint64_t Grad::max_val() {
	uint64_t ret = 0; 
	for (auto gradu : grads) { 
		//std::cout << "graud value is " << gradu.val <<std::endl; 
		if (gradu.val > ret)
			ret = gradu.val;
	}
	return ret;
}

void Grad::normalize() {
	double max_grad = (double)max_val();
	if (max_grad > 0.0) {
		for(auto &grad : grads) {
			grad.pct = 1.0 * ((double)grad.val / max_grad);
		}
	}
}

void Grad::clear() {
	for (auto gradu : grads) {
		gradu.val = 0;
		gradu.pct = 0.0;
	} 
}

size_t Grad::len() {
	return grads.size();
}


uint64_t Grad::val_sum() {
	uint64_t ret = 0;
	for (auto gradu : grads) {
		//FIXME: saturating_add
		ret += gradu.val;
	}
	return ret;
}

