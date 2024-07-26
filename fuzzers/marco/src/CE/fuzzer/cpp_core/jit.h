#ifndef UTIL_H_
#define UTIL_H_
#include "rgd.pb.h"

using namespace rgd;

int addFunction(const AstNode* request,
		std::unordered_map<uint32_t,uint32_t> &local_map,
    uint64_t id );
test_fn_type performJit(uint64_t id);
#endif
