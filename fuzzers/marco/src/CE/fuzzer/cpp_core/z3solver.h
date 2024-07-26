#ifndef Z3_SOLVER_H_
#define Z3_SOLVER_H_

#include "rgd.pb.h"
using namespace rgd;
#include <z3++.h>
#include <fstream>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <vector>


extern z3::context g_z3_context;

class Solver {
public:
  Solver();
  void add(z3::expr expr);
	void reset();
  bool check(std::unordered_map<uint32_t,uint8_t> &solu);
  bool checkonly();
	z3::expr serialize(const AstNode* req, 
						std::unordered_map<uint32_t,z3::expr> &expr_cache);

protected:
  z3::context&          context_;
  z3::solver            solver_;
  uint64_t              start_time_;
  uint64_t              solving_time_;
  uint64_t              solving_count_;

  std::vector<uint8_t> getConcreteValues();

	inline z3::expr cache_expr(uint32_t label, z3::expr const &e, 
						std::unordered_map<uint32_t,z3::expr> &expr_cache);

};

extern Solver* g_solver;


#endif // Z3_SOLVER_H_
