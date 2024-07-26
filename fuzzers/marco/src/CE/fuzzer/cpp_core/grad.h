#ifndef GRAD_H
#define GRAD_H
#include <vector>
#include <stdint.h>
#include <stddef.h>
class GradUnit {
	public:
		bool sign;
		uint64_t val;
		double pct;
};


class Grad {
	private: 
		std::vector<GradUnit> grads;
	public:
		Grad(size_t size);
    Grad() {};
    void set_len(size_t size) {grads.resize(size);}
		std::vector<GradUnit>& get_value();
		uint64_t max_val();
		void clear(); 
		size_t len();
		uint64_t val_sum();
		void normalize();
    void print();
};
#endif
